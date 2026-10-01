import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Empty, ErrorState, Loading, ModeBadge } from "@/components/common";
import { PatientTable } from "@/components/patient-table";
import type { Patient } from "@/types";

describe("research UI states", () => {
  it("makes output provenance explicit for every supported mode", () => {
    const { rerender } = render(<ModeBadge mode="demo" />);
    expect(screen.getByText("Output mode: Demo")).toBeVisible();
    rerender(<ModeBadge mode="inference" />);
    expect(screen.getByText("Output mode: Inference")).toBeVisible();
    rerender(<ModeBadge mode="precomputed" />);
    expect(screen.getByText("Output mode: Precomputed")).toBeVisible();
  });
  it("exposes accessible loading and recoverable errors", () => {
    const retry = vi.fn();
    const { rerender } = render(<Loading />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    rerender(<ErrorState message="API unavailable" onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("API unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });
  it("handles empty patient lists without fabricated records", () => {
    render(<PatientTable patients={[]} />);
    expect(screen.getByText("No patients yet")).toBeVisible();
  });
  it("does not display missing scores or confidence as calculated values", () => {
    const patient = {
      id: "p1",
      code: "CASE_1",
      age: null,
      sex: null,
      visitCount: 0,
      latestAnalysis: null,
      latestCompleted: null,
    } as Patient;
    render(<PatientTable patients={[patient]} />);
    expect(screen.getByText("Not analyzed")).toBeVisible();
    expect(screen.queryByText(/confidence/i)).toBeNull();
    expect(
      screen.getByRole("link", { name: /CASE_1 Age unspecified/ }),
    ).toHaveAttribute("href", "/patients/p1");
  });
  it("provides actionable empty states", () => {
    render(<Empty title="No visits">Add a baseline scan.</Empty>);
    expect(screen.getByText("Add a baseline scan.")).toBeVisible();
  });
});
