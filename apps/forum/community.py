"""Default GCD group names from the FAQ. No external destinations or DB writes."""

DEFAULT_GROUPS = (
    ("Main", ("gcd-main", "gcd-tech", "gcd-policy", "gcd-chat", "gcd-mycomics-users")),
    ("International", ("gcd-canada", "gcd-deutschland", "gcd-france", "gcd-italia",
                       "gcd-nederland-vlaanderen", "gcd-norge", "gcd-sverige", "gcd-uk")),
    ("Specialized", ("gcd-editor", "gcd-board", "gcd-error", "gcd-contact")),
)


def group_directory(categories):
    """Connect defaults only to explicitly configured categories; don't invent data."""
    by_slug = {category.slug: category for category in categories}
    used = set()
    sections = []
    for title, names in DEFAULT_GROUPS:
        groups = []
        for name in names:
            category = by_slug.get(name)
            if category:
                used.add(category.slug)
            groups.append({"name": name, "category": category})
        sections.append({"title": title, "groups": groups})
    custom = [{"name": category.name, "category": category}
              for category in categories if category.slug not in used]
    if custom:
        sections.append({"title": "Other groups", "groups": custom})
    return sections
