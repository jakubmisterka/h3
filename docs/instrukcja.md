# Bot do pre-game turniejów HotA – instrukcja

Bot na Discordzie dla społeczności Heroes of Might and Magic III (Horn of the Abyss). Przeprowadza **całą fazę przed grą** meczu turniejowego, zanim gracze wejdą do lobby: rzut monetą, bany i picki szablonów, losowanie miast, licytację o miasto, paczkę AI i kolor, losowanie bohaterów (ruletka), a na końcu podaje gotowe ustawienia do wpisania w lobby.

Obsługuje turnieje organizowane przez h3.gg. Wszystkie formaty turniejów to pliki JSON w repozytorium, więc każdy może dodać nowy przez pull request (zob. [Dla organizatorów](#dla-organizatorów-i-kontrybutorów)).

> **Zrzuty ekranu.** Przykłady poniżej są prawdziwymi wiadomościami bota, wygenerowanymi z aktualnych plików turniejów. Miejsca na zrzuty ekranu z Discorda są opisane w [obrazy/README.md](obrazy/README.md).

## Spis treści

1. [Najważniejsze zasady](#najważniejsze-zasady)
2. [Komendy](#komendy)
3. [Przebieg meczu krok po kroku](#przebieg-meczu-krok-po-kroku)
4. [Wybór szablonów: bany i picki](#wybór-szablonów-bany-i-picki)
5. [Handel (trade)](#handel-trade)
6. [Rodzaje handlu](#rodzaje-handlu)
7. [Ustawienia lobby](#ustawienia-lobby)
8. [Cofanie, status i wznawianie](#cofanie-status-i-wznawianie)
9. [Komenda /info](#komenda-info)
10. [Turnieje dostępne w bocie](#turnieje-dostępne-w-bocie)
11. [Pytania i problemy](#pytania-i-problemy)
12. [Dla organizatorów i kontrybutorów](#dla-organizatorów-i-kontrybutorów)

---

## Najważniejsze zasady

- **Jeden mecz = jeden wątek.** `/match start` tworzy wątek. Wszystko, co dotyczy meczu, dzieje się w tym wątku.
- **Tylko dwóch graczy.** Komendy meczu działają tylko dla dwóch graczy z wątku. Nikt inny ich nie użyje.
- **Bot nie ma bazy danych.** Stan meczu to wiadomości samego bota w wątku, zaczynające się znacznikiem w rodzaju `[#7 tb g1]` (numer, rodzaj kroku, numer gry). **Nie usuwaj i nie edytuj wiadomości bota.** Jeśli czegoś brakuje, bot nie zgaduje, tylko mówi, że nie może odczytać meczu.
- **Gracz A to zwycięzca rzutu monetą**, B to drugi gracz. A zaczyna bany i licytacje.
- **Co widzisz tylko Ty.** Potwierdzenia komend (np. „You banned 6lm10a.") i błędy widzi tylko osoba, która wpisała komendę. Reszta (zapis kroku, co dalej) trafia do wątku.
- **Kwoty złota** są zawsze w pełnych setkach i zapisywane ze spacją (`10 000`).
- **Bot niczego nie wymyśla.** Jeśli reguły turnieju czegoś nie określają, jest to zapisane jako otwarte pytanie, a nie zgadnięte.

## Komendy

| Komenda | Do czego | Kto |
|---|---|---|
| `/match start` | Rozpoczyna mecz: tworzy wątek, rzuca monetą i prowadzi do pierwszego kroku. Opcje: `opponent`, `mode`, `phase` (tylko gdy tryb ma kilka faz), `template` (gra od razu na jednym szablonie, jedna gra). | każdy, w zwykłym kanale tekstowym |
| `/ban` | Banuje szablon, gdy jest Twoja kolej. | gracz w wątku |
| `/pick` | Wybiera szablon, gdy jest Twoja kolej. | gracz w wątku |
| `/trade start` | Otwiera handel gry (numer, szablon albo bez parametru: pierwsza gra, która nie jest skończona). | gracz w wątku |
| `/trade roll` | Płaci za nowe losowanie miast i banuje miasta z obecnej pary (do limitu). | gracz w wątku |
| `/trade skip-roll` | Rezygnuje z losowania na obecnych miastach. | gracz w wątku |
| `/trade report` | Zgłasza wynik licytacji: `winner`, `amount`, `choice`. | gracz w wątku |
| `/trade ban-heroes` | Banuje bohaterów przed losowaniem (tylko ruletka). | gracz w wątku |
| `/match status` | Pokazuje stan meczu i zapisane kroki. | gracz w wątku |
| `/match undo` | Prosi o cofnięcie od wskazanego zapisu, albo się na nie zgadza. | gracz w wątku |
| `/info` | Opisuje tryb turnieju albo szablon w nim. Odpowiedź tylko dla Ciebie, można użyć wszędzie. | każdy |

Komendy podpowiadają wartości (szablony, miasta, kolory, bohaterów), więc zwykle wystarczy wybrać z listy.

---

## Przebieg meczu krok po kroku

Przykład: faza grupowa Mistrzostw Polski, jedna gra, szablon wybierany przez dwa bany i „decider".

### 1. Start

Anna wpisuje `/match start` i wybiera przeciwnika oraz tryb. Bot tworzy wątek i pisze zasady fazy, a potem losuje, kto jest A:

```
[#1 ms] Match started: <@1> vs <@2>
Mode: Mistrzostwa Polski 2026 (`mp2026`)
Phase: `Group phase`
Format: BO1
Template Selection: AB
A bans, B bans, then decider
Templates: Jebus Cross, 6lm10a, h3dm1
[#2 cf] Coinflip: <@1> wins and is A, so <@1> bans first. <@2> is B.
Remaining (3): Jebus Cross, 6lm10a, h3dm1
Step 1 of 2: <@1> bans a template with /ban
```

<!-- ![Start meczu](obrazy/01-start-meczu.png) -->

### 2. Bany szablonów

Anna: `/ban template:6lm10a`. Potem Boris: `/ban template:Jebus Cross`. Ostatni szablon zostaje grą:

```
[#4 bn] <@2> banned **Jebus Cross** (`JC`)
Remaining (1): h3dm1
Banned: 6lm10a, Jebus Cross. Picked: none.
The bans and picks are done. The games:
Game 1: h3dm1
Game 1 is h3dm1. Start its trade with /trade start.
More about this template: /info with mode `mp2026` and template `h3dm1`
```

### 3. Handel

`/trade start` otwiera handel gry. Bot podaje, co trzeba wiedzieć o szablonie, i od razu pierwszy krok:

```
Timer: `18:00+07:00+01:30`
Sim turns: `117`
Trade: one town for both players; town roll, then a bid for the color.
[#5 tr g1] Game 1 (h3dm1)
Town: `Cove`
Starting gold: 10 000
Next step: town roll
Cost: 500 gold
<@1>: 1 roll left
<@2>: 1 roll left
Roll with /trade roll (it bans this town); skip with /trade skip-roll
```

<!-- ![Otwarcie handlu](obrazy/02-otwarcie-handlu.png) -->

Szczegóły handlu są w [osobnym rozdziale](#handel-trade).

### 4. Ustawienia lobby

Po ostatniej licytacji bot podaje podsumowanie (zob. [Ustawienia lobby](#ustawienia-lobby)), a potem informuje, co dalej: następna gra, następny ban/pick, albo że każda gra jest załatwiona.

Dalej: wchodzicie do lobby HotA i wpisujecie to, co podał bot. **Wynik meczu zgłaszacie tak, jak ustala regulamin turnieju (np. na h3.gg)**. Bot nie śledzi wyników gier.

---

## Wybór szablonów: bany i picki

Sposób wyboru jest zapisany w formacie fazy i jest opisany w `/info`. Zapis „ABABABBA" czytamy po kolei: A banuje, B banuje, A wybiera (pick), B wybiera, A banuje, B banuje, B banuje, A banuje, a ostatni szablon trafia do „decidera" (ostatnia gra).

- **Bany i picki.** `/ban` i `/pick` w swojej kolei. Bot po każdym kroku pokazuje, co zostało (`Remaining`), kto co zbanował i czyja kolej.
- **Pick** ustala szablon kolejnej gry w kolejności pików. Decider, jeśli jest, to ostatnia gra. Handel gry można zacząć, gdy jej szablon jest już znany, także zanim skończą się bany.
- **Mecz na jednym szablonie.** Jeśli przy `/match start` podasz `template`, mecz ma jedną grę na tym szablonie, bez banów, i bot od razu otwiera handel. W fazach, w których gracze uzgadniają szablon, podanie go jest obowiązkowe.
- **Faza „fixed" (jeden szablon na cały mecz).** Niektóre turnieje grają wszystkie gry meczu na jednym szablonie (np. Sapphire Battlegrounds 3). Wtedy nie podajesz szablonu, nie ma banów, a bot po kolei zapowiada kolejne gry.
- **Ligi i mecze BO2.** W lidze bany/picki to zwykle ban–ban–pick–pick. Szablony, których nikt nie zbanował ani nie wybrał, po prostu nie są grane.
- **Pomyłka?** Cofnij ją komendą `/match undo` (zob. [Cofanie](#cofanie-status-i-wznawianie)).

---

## Handel (trade)

Handel to wszystko, co dzieje się po wyborze szablonu, a przed wejściem do gry: miasta, kolor i (w ruletce) bohaterowie. Bot losuje i pilnuje złota, a Wy zgłaszacie wyniki licytacji, które ustalacie między sobą (na czacie, w rozmowie głosowej), tak jak zawsze.

### Złoto

Każdy gracz zaczyna z pulą złota zależną od trudności szablonu: **160% = 10 000**, 130% = 15 000, 100% = 20 000. Bot liczy różnicę względem startu (`Gold difference: <@1> +500, <@2> -500`) i pilnuje, żeby nikt nie zapłacił więcej, niż ma. Wszystkie płatności idą do przeciwnika, więc suma jest stała.

Szablony 200% nie mają jeszcze handlu w bocie (rzut o kolor, losowe miasta), więc dla nich bot mówi, że handlu nie ma.

### Losowanie miast (roll)

Bot losuje parę miast (albo jedno miasto na szablonach lustrzanych). Każdy gracz może raz zapłacić za nowe losowanie:

- `/trade roll` – płacisz koszt losowania (domyślnie 500 złota, zależnie od turnieju i szablonu) przeciwnikowi i **banujesz** do dwóch miast z obecnej pary (opcje `ban_1`, `ban_2`). Bot losuje nową parę bez zbanowanych miast. Na szablonach lustrzanych banujesz jedyne miasto.
- `/trade skip-roll` – rezygnujesz z losowania na obecnych miastach. Jeśli przeciwnik zrobi roll i miasta się zmienią, możesz znów wybrać.
- Etap losowania kończy się, gdy nikt już nie może lub nie chce losować.

```
[#6 rl g1] Game 1 - <@2> rolled, banning `Cove`, and paid 500 gold to <@1>.
New town: `Necropolis`
Gold difference: <@1> +500, <@2> -500
Next step: town roll
Cost: 500 gold
<@1>: 1 roll left
<@2>: 0 rolls left
Roll with /trade roll (it bans this town); skip with /trade skip-roll
```

Przy „skip" bot dopisuje przy graczu `(skipped)`. Losowanie możesz zrobić bez banowania, jeśli nie podasz `ban_1`.

### Licytacja i zgłaszanie wyniku

Licytacja odbywa się **poza botem**. Zaczyna A, kolejne oferty rosną co najmniej o 100. Kiedy ustalicie wynik, **jeden z graczy** wpisuje:

```
/trade report winner:@Boris amount:300 choice:red
```

- `winner` – kto wygrał licytację,
- `amount` – ile płaci przeciwnikowi (pełne setki; `0`, jeśli nikt nie licytował),
- `choice` – wybór zwycięzcy: miasto z pary, `pack1`/`pack2` (paczka AI), `red`/`blue` (kolor), `hero`/`color` (ruletka lustrzana). Bot podpowiada właściwe wartości w danym kroku.

```
[#8 cb g1] Game 1 - Color bid, reported by <@2>
<@2> won at `300` gold and plays `red`
<@1> plays blue
Gold difference: <@1> +800, <@2> -800
```

Jeśli kwota jest nieprawidłowa (nie setki, więcej niż ma zwycięzca) albo wybór nie pasuje do kroku, bot odmawia i mówi dlaczego.

---

## Rodzaje handlu

Rodzaj handlu zależy od szablonu i fazy turnieju. Bot mówi o nim w zasadach (`Trade: ...`) i w `/info`.

| Rodzaj | Kroki |
|---|---|
| **Standardowy** | losowanie pary miast → licytacja o miasto → licytacja o kolor |
| **Lustrzany** (szablon lustrzany) | losowanie jednego miasta → licytacja o kolor (bohaterów wybieracie sami, według zasad turnieju, które znajdziesz w `/info`) |
| **Z paczkami AI** (np. Sapphire) | para miast + dwie paczki po trzy miasta AI → licytacja o miasto → o paczkę → o kolor |
| **Ruletka** | losowanie miast → bany bohaterów → bot losuje bohaterów → licytacje |
| **Ruletka z paczkami AI** | jak ruletka, plus paczki AI i licytacja o paczkę |

### Ruletka bohaterów

W ruletce bohaterów losuje bot (zamiast zewnętrznej strony). Bohaterowie pochodzą z wylosowanych miast i z listy dozwolonych na danym szablonie (bot zna listy zbanowanych i odblokowanych bohaterów dla każdego szablonu).

- Po losowaniu miast każdy gracz może zbanować określoną liczbę bohaterów (`/trade ban-heroes`, bez parametrów = nikogo). Najpierw A, potem B.
- Bot losuje bohaterów i podaje ich z linkiem do wiki.
- **Nielustrzany:** licytacja o miasto (zwycięzca dostaje miasto razem z jego bohaterem), potem o kolor.
- **Lustrzany:** jedna licytacja. Zwycięzca wybiera, czy najpierw wybiera bohatera, czy kolor, a drugi gracz dostaje resztę.
- W niektórych turniejach bohaterowie są losowani razem z miastami (wtedy nie ma banów), co opisuje `/info`.

Przykład: ruletka na szablonie lustrzanym (King of h3dm2, od 1/8 finału).

```
[#8 hd g1] Game 1 - The heroes are drawn:
`Spadum` <https://heroes.thelazy.net/index.php/Spadum>
`Akka` <https://heroes.thelazy.net/index.php/Akka>
Next step: bid for the first choice
<@1> bids first, raising by at least 100
Its winner chooses first either the hero or the color, and the other player chooses the other
Report the result with /trade report, choosing hero or color
```

<!-- ![Ruletka bohaterów](obrazy/03-ruletka-bohaterow.png) -->

---

## Ustawienia lobby

Gdy ostatnia licytacja jest zgłoszona, bot podaje, co wpisać w lobby. Na górze pojawiają się ustawienia, które w turnieju są określone (timer, rozmiar mapy, drogi, gracze komputerowi), a pod nimi to, co ustaliliście w handlu. **Gracz czerwony jest zawsze pierwszy.**

```
Game 1 lobby settings - h3dm1
Timer: 18:00+07:00+01:30
Map: L+U
Roads: mid
No AI players
Town (both players): Necropolis
<@2>: red, gold -800
<@1>: blue, gold +800
```

Przy szablonie z paczkami AI w linii gracza pojawia się jego paczka (`pack2 (Stronghold, Fortress, Cove)`), a w ruletce bohater przy mieście (`Castle (Orrin)`). Liczba przy graczu to jego różnica w złocie względem startu (po licytacjach i płatnościach za losowanie): o tyle zyskał lub stracił złota.

<!-- ![Ustawienia lobby](obrazy/04-ustawienia-lobby.png) -->

---

## Cofanie, status i wznawianie

### `/match status`

Pokazuje stan meczu: kto jest A, jak idzie wybór szablonów, każdą grę (szablon, czy handel trwa, co dalej, różnica złota, paczki AI) oraz **numerowaną listę zapisanych kroków**, tak jak bot je odczytał z wątku.

```
Match: <@1> vs <@2>
Mode mp2026, phase Group phase
Coinflip: <@1> is A (acts first), <@2> is B
Template Selection: done
Game 1: h3dm1, trade done, gold difference <@1> +800 / <@2> -800

I read 8 record(s) in this thread:
1. match started: <@1> vs <@2>, mode mp2026, phase Group phase
...
8. game 1: <@2> won the color bid at 300, chose red
```

### `/match undo`

Cofa mecz do stanu **sprzed wskazanego zapisu** (numer jest w `[#7 ...]`). Dotyczy wszystkiego od tego zapisu do końca. Żadna wiadomość nie jest usuwana; bot tylko przestaje je liczyć.

1. Jeden gracz: `/match undo from:7`. Bot zapisuje prośbę.
2. **Drugi gracz** musi się zgodzić: `/match undo` (bez numeru).
3. Bot potwierdza i pokazuje, co dalej.

```
[#9 ur] <@1> asks to undo from record `7` (game 1: <@1> skipped the roll) and the 1 step after it. ...
<@2>, to agree, run /match undo
[#10 ud] <@2> agreed: the match is back to how it was before record `7`.
```

Start meczu i rzut monetą nie mogą być cofnięte. W ruletce nie da się cofnąć samego losowania bohaterów (cofasz ostatni ban, a losowanie powtarza się po nim).

### Wznawianie

`/trade start` na grze, której handel był już rozpoczęty, otwiera go ponownie i pokazuje różnicę złota do tej pory. Jeśli rozpoczniesz handel innej gry, otwarty handel zostaje zamknięty (bot to zaznacza). Można do niego wrócić.

---

## Komenda /info

`/info` pokazuje opis trybu lub szablonu w nim. Odpowiedź widzisz tylko Ty i możesz jej użyć w dowolnym kanale.

- `/info mode:mp2026` – fazy, ich format (BO), sposób wyboru szablonów i dodatkowe zasady.
- `/info mode:mp2026 template:Jebus Cross` – trudność, koszt losowania, timer, mapa, drogi, tury symultaniczne i dodatkowe zasady szablonu. Opcja `phase` zawęża odpowiedź do jednej fazy.

```
**Jebus Cross** in Mistrzostwa Polski 2026
160% difficulty
Roll: 500 gold, 1 per player, up to 2 towns banned
Built into HotA
Timer: 12:00+06:00+01:15
Map: XL
Roads: fast
No AI players
Sim turns until 116
```

### Wersje alternatywne szablonów

Niektóre turnieje pozwalają, za zgodą graczy, zagrać na innej wersji szablonu (np. `h3dm_nc` zamiast `h3dm1`). Bot przy otwarciu handlu pisze wtedy: ``By agreement the template can be changed to `h3dm1` ``, z linkiem do pobrania, jeśli wersja nie jest wbudowana w HotA. `/info` też ją opisuje. Bot **nie zapisuje**, na której wersji gracie, a gra liczy się według szablonu, z którym zaczęto mecz.

---

## Turnieje dostępne w bocie

Pliki turniejów są w katalogu [`formats/`](../formats/). Aktualna lista:

| Tryb (`mode`) | Turniej | Co ważnego |
|---|---|---|
| `mp2026` | Mistrzostwa Polski 2026 | faza grupowa BO1, eliminacje i finał BO3, bany/picki szablonów |
| `sapphire-battlegrounds-3` | Sapphire Battlegrounds 3 | tylko szablon Sapphire; faza szwajcarska BO1, puchar BO3; handel z paczkami AI |
| `king-of-h3dm2` | King of h3dm2 | `h3dm_nc` (alternatywa: `h3dm1`); od 1/16 finału ruletka bohaterów |
| `exotic-tournament-3` | Exotic Tournament III | dziewięć nietypowych szablonów; BO3, dogrywka BO1, finał BO5 |
| `liga-heroes-12` | Liga Heroes sezon 12 | dywizje 1–6 oraz Blitz (mecze BO2), dogrywki na h3dm, Liga Mistrzów BO3 |
| `el-classico` | El Classico | tryb testowy: BO3, ruletka na kilku szablonach |

Każdą fazę wybierasz przy `/match start` w opcji `phase`. Tryby z jedną fazą nie pytają o nią.

**Znane ograniczenia (stan na dziś):**

- Bot prowadzi fazę *przed* grą. Nie zapisuje wyników gier ani nie kończy meczu BO3 po dwóch wygranych.
- Szablony o trudności 200% nie mają jeszcze handlu w bocie.
- W meczach BO2 ligi zasady dopuszczają powtórzenie szablonu w obu grach. Bot tego nie oferuje (drugi pick nie może wybrać szablonu pierwszego).
- Faza szwajcarska Ligi Heroes i pula szablonów Ligi Mistrzów nie są w pełni określone w regulaminie, więc nie ma ich w bocie lub mają założenia opisane w pliku turnieju.

---

## Pytania i problemy

**Bot nie reaguje / mówi, że brakuje uprawnień.** Bot potrzebuje w kanale, w którym zaczynasz mecz: *View Channel*, *Send Messages*, *Create Public Threads* (albo *Create Private Threads* dla prywatnych wątków), *Send Messages in Threads* i *Read Message History*. Bot nazywa brakujące uprawnienia po imieniu.

**„Start a match in a normal text channel, not inside a thread."** `/match start` działa w zwykłym kanale tekstowym, nie w wątku.

**Komenda nie działa w wątku.** Komendy meczu działają tylko w wątku meczu i tylko dla dwóch graczy.

**Bot mówi, że nie może odczytać meczu.** Ktoś usunął albo zmienił wiadomość bota. Bot nie zgaduje, więc poproś organizatora o pomoc.

**Pomyliłem się przy zgłoszeniu.** `/match undo from:<numer>` i zgoda drugiego gracza.

**Kto zgłasza wynik licytacji?** Dowolny z dwóch graczy. Zwykle zwycięzca, ale przegrany też może.

**Czy bot sprawdza, czy jesteśmy w turnieju?** Nie. Bot ufa komendzie. Mecz towarzyski w trybie turniejowym też zadziała.

---

## Dla organizatorów i kontrybutorów

- **Dodanie turnieju** to dodanie pliku JSON w [`formats/`](../formats/) i, jeśli trzeba, szablonów w [`data/templates.json`](../data/templates.json). Opis wszystkich pól, przykłady i najczęstsze błędy są w [formats/README.md](../formats/README.md) (po angielsku). Format jest sprawdzany przy starcie bota i w testach, więc błąd w pliku nie przejdzie niezauważony.
- **Szablony i bohaterowie** (trudność, rozmiar mapy, drogi, link do pobrania, zbanowani i odblokowani bohaterowie) są w [data/README.md](../data/README.md).
- **Uruchomienie i konfiguracja bota** (tokeny, uprawnienia, Poetry, testy) są w głównym [README.md](../README.md).
- **Jak powstawał bot:** funkcje są najpierw opisane w specyfikacjach w [`openspec/`](../openspec/), a dopiero potem implementowane. Zasady turniejów, które nie są jasne, są w specyfikacjach zapisane jako „Open question".

Masz pomysł albo znalazłeś błąd? Otwórz issue lub pull request w repozytorium.
