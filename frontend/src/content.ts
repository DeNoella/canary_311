// Plain-language copy for the Home and "How it works" pages.
// Kept separate so the wording is easy to tweak without touching components.

export const TAGLINE =
  "Listening to a city's complaints to spot neighborhoods under stress.";

export const WHAT_IS_IT = [
  `When New Yorkers have a problem that isn't an emergency — a noisy neighbor,
   no heat, an overflowing trash can, a pothole — they call 311. The city logs
   millions of these calls a year. On their own they're just noise. Together,
   they're a pulse.`,
  `Canary asks a simple question: when a neighborhood's complaints start rising,
   does its housing market weaken soon after? Like the canary in a coal mine,
   the idea is that residents feel a place slipping before the official numbers
   show it.`,
];

export const HOW_TO_READ = [
  {
    k: "Each block is a ZIP code",
    v: "175 New York City ZIP codes, placed where they actually sit on the map.",
  },
  {
    k: "Height = how many complaints",
    v: "A taller block means more 311 calls from that ZIP in the selected month.",
  },
  {
    k: "Colour = complaint pressure",
    v: "Green means the call volume is normal for that area. Red means it's unusually high right now, compared with that ZIP's own recent history. Blocks that pulse are the ones climbing fastest.",
  },
  {
    k: "Press Play",
    v: "Watch three years (Sept 2022 – Aug 2025) play out month by month.",
  },
  {
    k: "Click a block",
    v: "See that neighborhood's story: its complaint trend next to home values, the time-shift comparison, and the specific issues people are calling about.",
  },
];

export const WHAT_WE_FOUND = [
  `Across 175 neighborhoods and about 9.9 million complaints over three years,
   rising complaints and a weakening housing market tend to move together — at
   roughly the same time, not one clearly ahead of the other. The link is real
   but weak.`,
  `The interesting exception: in the handful of neighborhoods where complaints
   climbed the fastest, the complaint surge showed up about six months before
   home-value growth slowed. That's a hint worth chasing, not proof — it's a
   small group and it could be chance.`,
  `Bottom line: 311 complaints are a useful thermometer for neighborhood stress,
   but on this data they are not a crystal ball. This is an exploratory look,
   not a forecast, and correlation is not cause.`,
];

export const HOW_IT_WORKS = [
  {
    step: "1",
    title: "Gather the calls",
    body: `Every NYC 311 service request from September 2022 to August 2025 —
           about 9.9 million of them — plus Zillow's Home Value Index (a
           widely-used estimate of typical home value) for the same ZIP codes
           and months.`,
  },
  {
    step: "2",
    title: "Find the themes",
    body: `A language model reads the text of each complaint and groups them into
           themes — noise, water & plumbing, trash, street conditions, and so on
           — on its own, without being handed a list of categories. Each theme
           gets a short auto-generated label from its most distinctive words.`,
  },
  {
    step: "3",
    title: "Measure the pressure",
    body: `For every ZIP code in every month we compute three things: how many
           complaints there were, how fast that number is changing, and how
           unusual it is compared with that ZIP's own trailing 12-month average
           (its "complaint pressure").`,
  },
  {
    step: "4",
    title: "Line it up against home values",
    body: `We compare each ZIP's complaint pressure against the change in its
           home values 0, 3, 6, and 12 months later, and measure how tightly the
           two move together — for individual ZIPs and pooled across all of
           them.`,
  },
  {
    step: "5",
    title: "Show it",
    body: `The pipeline writes a set of small data files; this website reads them
           and draws the 3D map, the charts, and the written summary you're
           looking at.`,
  },
];

export const TECH = [
  { k: "Data pipeline", v: "Python — pandas, scikit-learn, SciPy" },
  {
    k: "Theme discovery",
    v: "sentence-transformers (all-MiniLM-L6-v2) sentence embeddings + K-means clustering + TF-IDF labelling. Runs locally on a laptop CPU.",
  },
  { k: "API", v: "FastAPI (Python) serving the pipeline's output files" },
  {
    k: "This website",
    v: "React + Vite + TypeScript, with Three.js (via react-three-fiber) for the animated 3D map",
  },
  {
    k: "Cost",
    v: "$0. Everything runs locally on free, open-source tools and free public data. No paid APIs are used anywhere.",
  },
];

export const DATA_SOURCES = [
  {
    name: "NYC 311 Service Requests",
    what: `The City of New York's official log of every non-emergency service
           request residents make — by phone, app, or web. Fields used: date,
           complaint type, description text, ZIP code, borough, and location.`,
    how: `Normally pulled from NYC Open Data's public API. That API was
           unreachable from the build environment (every request was blocked), so
           the data was taken instead from a public Kaggle mirror of the same
           official dataset — a single ~12 GB CSV. It was streamed in chunks
           (never loaded whole), filtered to the three-year window, and reduced
           to true monthly complaint counts per ZIP plus a ~150,000-row sample of
           complaint text for the theme step.`,
  },
  {
    name: "Zillow Home Value Index (ZHVI), ZIP level",
    what: `Zillow's monthly estimate of the typical home value in a ZIP code
           (smoothed and seasonally adjusted). Used here as the "slower-moving"
           signal that complaint pressure is compared against.`,
    how: `Downloaded directly as a public CSV from Zillow's research data page —
           no account or key required — then reshaped to one value per ZIP per
           month.`,
  },
  {
    name: "Overlap",
    what: `Only ZIP codes present in both datasets are analysed — 175 of them.
           ZIPs that are mostly parks, airports, or PO boxes drop out naturally.`,
    how: "",
  },
];

export const LIMITATIONS = [
  "It's correlational, not causal. Many things move complaints and home prices at once — the seasons, the economy, new construction.",
  "One city, one three-year window. No test on other cities or other time periods.",
  "The complaint text is a monthly sample, not every single call.",
  "The home-value index is itself a smoothed, modelled estimate, and it doesn't cover every ZIP.",
  "With many ZIPs and several time-shifts compared, some 'significant' results are expected by chance.",
];
