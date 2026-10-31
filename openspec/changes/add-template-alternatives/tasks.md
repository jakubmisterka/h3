## 1. The setting

- [x] 1.1 Add `alternatives` to the settings a tournament can state for a template (`formats/schema.json`, `template_settings.py`), stacked like the timer, with pytest cases for the stacking
- [x] 1.2 Validate the alternatives when a format is loaded (known template, not itself, listed once, built in or with a download link), naming the template and the alternative, with pytest cases for each scenario of "A tournament can state alternatives for a template"
- [x] 1.3 Document `alternatives` in `formats/README.md` with a tested example, and note in `data/README.md` that an alternative needs a catalogue entry

## 2. The messages

- [x] 2.1 Add the line about the alternatives to `announcement_lines`, after the trade rule, with the link for each alternative that is not built in, with pytest cases for each scenario of "The thread names the alternatives of a template"
- [x] 2.2 Name the alternatives in the `/info` reply for a template, with the differences by phase, with pytest cases for each scenario of "The template reply names its alternatives"

## 3. Check

- [x] 3.1 For the maintainers: add the alternative templates to `data/templates.json` and state them in the formats that allow them
- [ ] 3.2 Milestone check in the dev guild: start a trade on a template with an alternative (by `/trade start` and by a named template) and look up the template with `/info`
