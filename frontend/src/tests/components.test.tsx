import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";
import type { HealthEvidence } from "../api/contracts";
import { DrawerProvider } from "../app/providers";
import { Drawer } from "../components/Drawer";
import { HealthEvidencePanel } from "../components/EvidencePanel";
import { MarkerTabs } from "../components/Selectors";
import { fmt, signed } from "../lib/format";

// Shape mirrors the backend evidence object; values copied from the pinned OSD-575 snapshot (C001 L-3 creatinine).
const ev: HealthEvidence = {
  schema_version: "1.0",
  evidence_id: "osd575-cmp:C001_serum_L-3:creatinine",
  kind: "HEALTH_OBSERVATION",
  case: "health",
  title: "Creatinine · C001 · L-3",
  source: {
    dataset_id: "OSD-575-CMP", title: "Inspiration4 CMP", provider: "NASA OSDR",
    file_name: "LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv", sha256: "5eb1e7f0".padEnd(64, "0"),
    source_url: "https://osdr.nasa.gov/bio/repo/data/studies/OSD-575", download_url: "", fetched_at: null, imported_at: "2026-11-14T00:00:00Z",
    license_note: "CC0-1.0", citation: "", source_row: 1, file_line: 2, sample_name: "C001_serum_L-3",
    source_columns: { value: "creatinine_value_milligram_per_deciliter", range_min: "", range_max: "" }, raw_value: "1.37", source_unit: "milligram_per_deciliter",
  },
  context: { participant_id: "C001", sample_id: "C001_serum_L-3", phase: "PREFLIGHT", visit: "L-3", visit_label: "L-3 · Preflight", relative_day: -3, relative_day_reference: "days before launch" },
  measurement: { marker: "creatinine", marker_name: "Creatinine", value: 1.37, unit: "mg/dL", range_low: 0.6, range_high: 1.35, range_status: "ABOVE_SUPPLIED_UPPER_BOUND", needs_review: true },
  comparison: {
    method: "retrospective_preflight_arithmetic_mean", baseline: 1.2366666667, n: 3, baseline_available: true,
    baseline_values: [{ visit: "L-92", sample_id: "", value: 1.24, source_row: 3 }, { visit: "L-44", sample_id: "", value: 1.1, source_row: 2 }, { visit: "L-3", sample_id: "", value: 1.37, source_row: 1 }],
    includes_selected_sample: true, delta: 0.1333333333, percent_delta: 10.78167, rule_version: "health-compare-v1", formulas: {},
  },
  evidence_strength: "DIRECT_RESEARCH_MEASUREMENT_WITH_DESCRIPTIVE_COMPARISON",
  limitations: ["Not a diagnosis."],
  review: null,
};

afterEach(() => vi.restoreAllMocks());

describe("format", () => {
  it("rounds only for presentation and keeps signs explicit", () => {
    expect(fmt(1.2366666667)).toBe("1.2367");
    expect(fmt(90)).toBe("90");
    expect(signed(12.6666667, 2)).toBe("+12.67");
    expect(signed(-0.5, 2)).toBe("−0.5");
    expect(fmt(null)).toBe("—");
    // Regression: integers with trailing zeros must not be truncated (axis showed "3" for 300).
    expect(fmt(300, 0)).toBe("300");
    expect(fmt(150, 1)).toBe("150");
    expect(fmt(1.1)).toBe("1.1");
  });
});

describe("HealthEvidencePanel", () => {
  it("shows observed → compared → source → limits → follow-up with status in text, not only colour", () => {
    render(<DrawerProvider><HealthEvidencePanel ev={ev} followUp={<button>Record follow-up</button>} /></DrawerProvider>);
    const labels = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(labels).toEqual(["Observation", "Calculation", "Source & quality", "Limitations", "Follow-up"]);
    expect(screen.getByText("Outside supplied range · above upper bound")).toBeInTheDocument();
    expect(screen.getByText("1.2367 mg/dL (n = 3)")).toBeInTheDocument();
    expect(screen.getByText(/Data row 1 \(file line 2\)/)).toBeInTheDocument();
    expect(screen.getByText(/comparison is retrospective/)).toBeInTheDocument();
  });
});

describe("MarkerTabs", () => {
  it("supports arrow-key navigation and announces flagged markers", async () => {
    function Harness() {
      const [v, setV] = useState("glucose");
      return <MarkerTabs markers={[{ id: "glucose", label: "Glucose" }, { id: "creatinine", label: "Creatinine" }]} value={v} onChange={setV} flagged={new Set(["creatinine"])} panelId="p" />;
    }
    render(<Harness />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("tab", { name: "Glucose" }));
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /Creatinine/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /outside supplied range/ })).toBeInTheDocument();
  });
});

describe("Drawer", () => {
  it("is a labelled modal dialog that closes on Escape", async () => {
    const onClose = vi.fn();
    render(<Drawer title="Evidence" onClose={onClose}><button>Inside</button></Drawer>);
    expect(screen.getByRole("dialog", { name: "Evidence" })).toHaveAttribute("aria-modal", "true");
    await userEvent.setup().keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
