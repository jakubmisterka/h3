## 1. The field

- [x] 1.1 Add `rules_link` to `formats/schema.json` and to `Format`, check that it starts with `https://`, with pytest cases for each scenario of "A tournament can link to its rules"

## 2. Showing it

- [x] 2.1 Post `Rules: [full tournament rules](<link>)` after the number of games at the start of a match, with pytest cases for each scenario of "The rules at the start of a match link to the tournament's rules"
- [x] 2.2 Show it in `/info` for a mode, with pytest cases for each scenario of "Mode info links to the tournament's rules"

## 3. Data and docs

- [x] 3.1 State the link in the shipped formats that have a published ruleset
- [x] 3.2 Document `rules_link` in `formats/README.md` and in the Polish guide
