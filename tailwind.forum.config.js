/** Isolated forum stylesheet. Build with Tailwind 3.4.1. */
module.exports = {
  content: [
    './apps/forum/templates/forum/**/*.html',
    './apps/forum/forms.py',
    './apps/forum/templatetags/forum_tags.py',
    './templates/gcd/fine_print.html',
  ],
  theme: { extend: {} },
  plugins: [require('@tailwindcss/forms')],
};
