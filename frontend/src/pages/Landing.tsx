import { useEffect } from "react";
import { Link } from "react-router-dom";
import {
  BrandMark, IconArrow, IconBan, IconCheck, IconLog, IconOverview, IconRadiation, IconSatellite, IconTrend,
} from "../components/icons";

const WORKSPACE = "/overview?participant=C001&sample=L-3";

const STEPS = [
  { to: WORKSPACE, n: "01", title: "Health Overview", Icon: IconOverview,
    text: "Five blood markers for one historical sample, compared with the supplied laboratory range and the participant's own preflight values." },
  { to: "/health?participant=C001&sample=L-3&marker=creatinine", n: "02", title: "Health Trends", Icon: IconTrend,
    text: "Every real visit for one marker, in order. The retrospective preflight mean is kept apart from what was known before each visit." },
  { to: "/environment", n: "03", title: "Radiation Review", Icon: IconRadiation,
    text: "A separate ISS sensor record. Dose rate, estimated accumulated sensor dose, and every excluded reading you can inspect." },
  { to: "/reviews", n: "04", title: "Review Log & Export", Icon: IconLog,
    text: "Saved follow-ups with history, exported as a local JSON or HTML packet that carries hashes, source rows and limitations." },
];

const VISITS = ["L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"];

/** Static public introduction. It makes no API calls; every image is bundled locally. */
export default function Landing() {
  useEffect(() => {
    document.title = "CytoZoe — Understand the change. Keep the evidence.";
  }, []);

  return (
    <div className="landing">
      <a className="skip-link" href="#intro">Skip to content</a>
      <header className="l-top">
        <div className="l-wrap">
          <Link to="/" className="l-brand" aria-label="CytoZoe home"><BrandMark />CytoZoe</Link>
          <div className="l-top-right">
            <span className="l-tag">Research prototype</span>
            <Link to={WORKSPACE} className="l-btn l-btn-ghost l-btn-sm">Open workspace</Link>
          </div>
        </div>
      </header>

      <main id="intro" tabIndex={-1}>
        <section className="l-hero" aria-labelledby="hero-title">
          <div className="l-hero-media">
            <picture>
              <source media="(max-width: 700px)" type="image/avif" srcSet="/media/earth-sunrise-hero-mobile.avif" />
              <source media="(max-width: 700px)" type="image/webp" srcSet="/media/earth-sunrise-hero-mobile.webp" />
              <source type="image/avif" srcSet="/media/earth-sunrise-hero-1440.avif 1440w, /media/earth-sunrise-hero-2400.avif 2400w" sizes="100vw" />
              <source type="image/webp" srcSet="/media/earth-sunrise-hero-1440.webp 1440w, /media/earth-sunrise-hero-2400.webp 2400w" sizes="100vw" />
              <img src="/media/earth-sunrise-hero-1440.webp" alt="" width={1440} height={809} fetchPriority="high" decoding="async" />
            </picture>
          </div>
          <div className="l-hero-shade" aria-hidden="true" />
          <div className="l-hero-grid" aria-hidden="true" />
          <p className="l-photo-cap">Sunrise over Earth's limb, seen from the ISS<br />ISS067-E-245176 · 6 Aug 2022 · NASA JSC</p>

          <div className="l-wrap">
            <div className="l-hero-body">
              <p className="l-kicker">NASA Space Apps Challenge 2026</p>
              <h1 id="hero-title" className="l-title">Understand the change. <span>Keep the evidence.</span></h1>
              <p className="l-sub">
                An offline-first research workspace for reviewing historical astronaut health measurements and recording
                source-linked follow-ups.
              </p>
              <div className="l-cta">
                <Link to={WORKSPACE} className="l-btn l-btn-primary">Launch Workspace<IconArrow /></Link>
                <a href="#how" className="l-btn l-btn-ghost">Explore the system</a>
              </div>
              <p className="l-disclosure">
                <span>Independent research prototype</span>
                <span>Historical NASA research data, not live telemetry</span>
                <span>Runs offline after setup</span>
              </p>
            </div>
            <div className="l-props">
              <div className="l-prop"><b aria-hidden="true">01</b><div><h2>Compare real measurements</h2><p>Each value comes straight from a verified NASA research file.</p></div></div>
              <div className="l-prop"><b aria-hidden="true">02</b><div><h2>Verify the evidence</h2><p>See the exact file, row, column, rule and limitations behind every number.</p></div></div>
              <div className="l-prop"><b aria-hidden="true">03</b><div><h2>Record the follow-up</h2><p>Save a note and status locally, then export a source-linked review packet.</p></div></div>
            </div>
          </div>
        </section>

        <section id="how" className="l-section" aria-labelledby="how-title" tabIndex={-1}>
          <div className="l-wrap">
            <div className="l-head">
              <p className="l-kicker">How it works</p>
              <h2 id="how-title">Four screens. One question each.</h2>
              <p>Every number is calculated by the local service from the verified source file. The interface only displays it, with a path back to the row it came from.</p>
            </div>
            <ol className="l-steps">
              {STEPS.map(({ to, n, title, text, Icon }) => (
                <li key={n}>
                  <Link to={to} className="l-step" style={{ textDecoration: "none" }}>
                    <Icon />
                    <span className="n">{n}</span>
                    <h3>{title}</h3>
                    <p>{text}</p>
                  </Link>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="l-section alt" aria-labelledby="cases-title">
          <div className="l-wrap">
            <div className="l-head">
              <p className="l-kicker">Case studies</p>
              <h2 id="cases-title">Two real NASA research records. Kept apart.</h2>
              <p>Both files are pinned by SHA-256. If a file has been changed by even one byte, the local service refuses it and keeps the last verified data.</p>
            </div>
            <div className="l-cases">
              <article className="l-case" aria-labelledby="case-health">
                <figure className="l-case-media" style={{ margin: 0 }}>
                  <svg viewBox="0 0 560 245" role="img" aria-label="The seven sample visits per participant, from 92 days before launch to 194 days after return" style={{ width: "100%", height: "100%" }}>
                    <line x1="40" x2="520" y1="140" y2="140" stroke="rgb(148 178 204 / 35%)" strokeWidth="1" />
                    <line x1="240" x2="240" y1="84" y2="190" stroke="#35E1D5" strokeDasharray="3 5" strokeWidth="1" />
                    <text x="240" y="74" fill="#35E1D5" fontSize="11" textAnchor="middle" fontFamily="ui-monospace, monospace">FLIGHT</text>
                    {VISITS.map((v, i) => {
                      const x = 40 + i * 80;
                      return (
                        <g key={v}>
                          <circle cx={x} cy={140} r={i < 3 ? 6 : 7} fill={i < 3 ? "#0B1F32" : "#35E1D5"} stroke="#35E1D5" strokeWidth="1.5" />
                          <text x={x} y={172} fill="#C9D6E2" fontSize="12" textAnchor="middle" fontFamily="ui-monospace, monospace">{v}</text>
                        </g>
                      );
                    })}
                    <text x="40" y="112" fill="#9FB3C6" fontSize="11" fontFamily="ui-monospace, monospace">PREFLIGHT</text>
                    <text x="520" y="112" fill="#9FB3C6" fontSize="11" textAnchor="end" fontFamily="ui-monospace, monospace">POSTFLIGHT</text>
                  </svg>
                </figure>
                <div className="l-case-body">
                  <span className="tag">Health case · OSD-575</span>
                  <h3 id="case-health">Inspiration4 crew blood chemistry</h3>
                  <p>Serum comprehensive metabolic panel from the 2021 Inspiration4 mission, published in the NASA Open Science Data Repository. These are sparse blood draws, not continuous monitoring.</p>
                  <ul className="l-facts">
                    <li>4 anonymised participants</li><li>7 visits each</li><li>5 selected markers</li><li>Supplied lab ranges</li>
                  </ul>
                </div>
              </article>
              <article className="l-case" aria-labelledby="case-env">
                <figure className="l-case-media" style={{ margin: 0 }}>
                  <picture>
                    <source type="image/avif" srcSet="/media/earth-night-iss-800.avif 800w, /media/earth-night-iss-1600.avif 1600w" sizes="(max-width: 899px) 100vw, 50vw" />
                    <source type="image/webp" srcSet="/media/earth-night-iss-800.webp 800w, /media/earth-night-iss-1600.webp 1600w" sizes="(max-width: 899px) 100vw, 50vw" />
                    <img src="/media/earth-night-iss-800.webp" width={800} height={533} loading="lazy" decoding="async"
                      alt="City lights of Southeast Asia and lightning streak below the International Space Station at night" />
                  </picture>
                  <figcaption>NASA JSC · iss073e0257211 · decorative context, not study data</figcaption>
                </figure>
                <div className="l-case-body">
                  <span className="tag">Environment case · RadLab</span>
                  <h3 id="case-env">ISS Columbus DosTel1 radiation record</h3>
                  <p>One day of absorbed dose-rate readings from the DosTel1 instrument in the ISS Columbus module, from the NASA OSDR RadLab archive. Conflicting duplicate readings are quarantined, never averaged.</p>
                  <ul className="l-facts">
                    <li>1 March 2022</li><li>Absorbed dose rate, µGy/hour</li><li>Sensor dose, not personal dose</li>
                  </ul>
                </div>
              </article>
            </div>
            <p className="l-separate"><IconSatellite />Different missions, dates and people. CytoZoe never pairs the radiation record with any health participant.</p>
          </div>
        </section>

        <section className="l-section" aria-labelledby="trust-title">
          <div className="l-wrap">
            <div className="l-head">
              <p className="l-kicker">Scientific integrity</p>
              <h2 id="trust-title">Built to be trusted, not to impress.</h2>
            </div>
            <div className="l-trust">
              <div className="l-trust-card yes">
                <h3>What CytoZoe does</h3>
                <ul>
                  <li><IconCheck />Shows NASA data only when its SHA-256 matches a registered snapshot</li>
                  <li><IconCheck />Traces every value to its file, data row and column</li>
                  <li><IconCheck />Explains results with fixed, verified templates. There is no language model</li>
                  <li><IconCheck />Saves reviews in a local SQLite database and exports them as JSON or HTML</li>
                  <li><IconCheck />Works with the internet disconnected once it is set up</li>
                </ul>
              </div>
              <div className="l-trust-card no">
                <h3>What it never does</h3>
                <ul>
                  <li><IconBan />Diagnose, score risk or recommend treatment</li>
                  <li><IconBan />Claim live NASA telemetry or real-time astronaut monitoring</li>
                  <li><IconBan />Use AI predictions or invent missing values</li>
                  <li><IconBan />Link the radiation record to health outcomes</li>
                  <li><IconBan />Send your notes anywhere. Export is a local download</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        <section className="l-final" aria-labelledby="final-title">
          <div className="l-wrap">
            <h2 id="final-title">Open the evidence.</h2>
            <p>Start with participant C001's preflight sample L-3. There, one measured value sits just above the supplied laboratory range.</p>
            <Link to={WORKSPACE} className="l-btn l-btn-primary">Launch Workspace<IconArrow /></Link>
          </div>
        </section>
      </main>

      <footer className="l-footer" aria-labelledby="credits-title">
        <div className="l-wrap">
          <h2 id="credits-title">Photo &amp; data credits</h2>
          <div className="l-credits">
            <div>
              <p><strong>Hero photograph.</strong> Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center. ISS067-E-245176, 6 August 2022.</p>
              <p><a href="https://eol.jsc.nasa.gov/SearchPhotos/photo.pl?mission=ISS067&amp;roll=E&amp;frame=245176" rel="noreferrer noopener" target="_blank">eol.jsc.nasa.gov</a></p>
            </div>
            <div>
              <p><strong>Case-study photograph.</strong> NASA / Johnson Space Center, iss073e0257211, 17 June 2025. City lights and lightning below the ISS.</p>
              <p><a href="https://images.nasa.gov/details/iss073e0257211" rel="noreferrer noopener" target="_blank">images.nasa.gov</a></p>
            </div>
            <div>
              <p><strong>Data.</strong> NASA Open Science Data Repository OSD-575 (Inspiration4 CMP, LSDS-8) and NASA OSDR RadLab DosTel1 export for 1 March 2022.</p>
              <p><a href="https://osdr.nasa.gov/bio/repo/data/studies/OSD-575" rel="noreferrer noopener" target="_blank">osdr.nasa.gov</a></p>
            </div>
          </div>
          <div className="l-legal">
            <span>Independent research prototype · NASA Space Apps Challenge 2026. Not affiliated with or endorsed by NASA. Not a medical device.</span>
            <span>Photos are decorative context, bundled locally. External links need internet.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
