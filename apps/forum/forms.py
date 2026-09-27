from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from markdownx.fields import MarkdownxFormField

from .models import Category, Discussion, Post, Report, Tag
from .access import accessible_categories


INPUT_CLASS = (
    "w-full rounded-lg border-slate-300 bg-white text-slate-900 "
    "focus:border-indigo-500 focus:ring-indigo-500"
)


class DiscussionForm(forms.ModelForm):
    content = MarkdownxFormField(
        label="First post",
        widget=forms.Textarea(attrs={"rows": 8, "class": INPUT_CLASS}),
    )
    gcd_content_type = forms.ModelChoiceField(
        label="Related GCD entity type",
        queryset=ContentType.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": INPUT_CLASS}),
    )
    gcd_object_id = forms.IntegerField(
        label="Related GCD entity ID",
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS}),
    )

    class Meta:
        model = Discussion
        fields = ("title", "category", "tags")
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "category": forms.Select(attrs={"class": INPUT_CLASS}),
            "tags": forms.SelectMultiple(attrs={"class": INPUT_CLASS}),
        }

    def __init__(self, *args, user=None, ip_address=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.ip_address = ip_address
        self.fields["category"].label = "Community group"
        self.fields["title"].widget.attrs["placeholder"] = "What would you like to discuss?"
        self.fields["tags"].help_text = "Optional. Select tags to help others find this discussion."
        self.fields["gcd_object_id"].help_text = "Optional. The numeric ID from the GCD record URL."
        self.fields["category"].queryset = accessible_categories(user)
        self.fields["tags"].queryset = Tag.objects.all()
        self.fields["gcd_content_type"].queryset = ContentType.objects.filter(
            app_label="gcd"
        ).order_by("model")

    def clean(self):
        cleaned = super().clean()
        content_type = cleaned.get("gcd_content_type")
        object_id = cleaned.get("gcd_object_id")
        category = cleaned.get("category")
        if category and category.content_type_id:
            if (content_type and content_type.pk != category.content_type_id) or (object_id and object_id != category.object_id):
                raise ValidationError("The related record must match the selected group.")
            content_type, object_id = category.content_type, category.object_id
            cleaned["gcd_content_type"], cleaned["gcd_object_id"] = content_type, object_id
        if bool(content_type) != bool(object_id):
            raise ValidationError("Select both a GCD entity type and its ID.")
        if content_type:
            model = content_type.model_class()
            if model is None or not model._default_manager.filter(pk=object_id).exists():
                self.add_error("gcd_object_id", "The selected GCD entity does not exist.")
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError("DiscussionForm must be saved with commit=True.")
        discussion = super().save(commit=False)
        discussion.author = self.user
        discussion.created_by = self.user
        discussion.updated_by = self.user
        discussion.ip_address = self.ip_address
        discussion.content_type = self.cleaned_data.get("gcd_content_type")
        discussion.object_id = self.cleaned_data.get("gcd_object_id")
        discussion.save()
        self.save_m2m()
        Post.objects.create(
            discussion=discussion,
            author=self.user,
            content=self.cleaned_data["content"],
            created_by=self.user,
            updated_by=self.user,
            ip_address=self.ip_address,
        )
        return discussion


class PostForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Post.objects.none(), required=False, widget=forms.HiddenInput()
    )

    class Meta:
        model = Post
        fields = ("content", "parent")
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 5,
                    "class": INPUT_CLASS,
                    "placeholder": "Write a thoughtful reply…",
                }
            ),
            "parent": forms.HiddenInput(),
        }

    def __init__(self, *args, discussion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.discussion = discussion
        if discussion:
            self.fields["parent"].queryset = Post.objects.filter(
                discussion=discussion
            )

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")
        if parent and parent.discussion_id != self.discussion.pk:
            raise ValidationError("The parent post belongs to another discussion.")
        return parent


class DiscussionEditForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = accessible_categories(user)

    def clean_category(self):
        category = self.cleaned_data["category"]
        if category.content_type_id and (category.content_type_id != self.instance.content_type_id or category.object_id != self.instance.object_id):
            raise ValidationError("This discussion is linked to a different GCD record.")
        return category

    class Meta:
        model = Discussion
        fields = ("title", "category", "tags")
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "category": forms.Select(attrs={"class": INPUT_CLASS}),
            "tags": forms.SelectMultiple(attrs={"class": INPUT_CLASS}),
        }


class PostEditForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("content",)
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8, "class": INPUT_CLASS})
        }


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reason",)
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 4, "class": INPUT_CLASS})
        }


class GCDGroupForm(forms.Form):
    object_id = forms.IntegerField(label="GCD ID", min_value=1,
        widget=forms.NumberInput(attrs={"class": INPUT_CLASS}))

    def __init__(self, *args, parent, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent

    def clean_object_id(self):
        object_id = self.cleaned_data["object_id"]
        self.content_type = ContentType.objects.get(app_label="gcd", model=self.parent.entity_model)
        model = self.content_type.model_class()
        self.record = model._default_manager.filter(pk=object_id).first() if model else None
        if self.record is None or getattr(self.record, "deleted", False):
            raise ValidationError("GCD record not found.")
        return object_id
