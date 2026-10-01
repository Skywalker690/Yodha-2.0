import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { BaselineForecast } from "@/components/baseline-forecast";
import { useResource } from "@/lib/use-resource";

vi.mock("@/lib/use-resource", () => ({ useResource: vi.fn() }));
beforeEach(() => {
  vi.mocked(useResource).mockReturnValue({
    data: {
      prediction: {
        status: "partial",
        mode: "live",
        modelVersion: "synthetic",
        usedMri: false,
        fastsurferVersion: null,
        probabilities: { "12": null, "24": null, "36": 0.2 },
        calibration: {},
        warnings: ["Synthetic support warning"],
        explanation: {},
      },
      qc: "unavailable",
      anatomy: null,
    },
    loading: false,
    error: "",
    reload: vi.fn(),
  });
});
it("shows missing horizons as unavailable and separates the forecast target", () => {
  render(<BaselineForecast patientId="synthetic-p" />);
  expect(screen.getAllByText("Unavailable")).toHaveLength(2);
  expect(screen.getByText("20.0%")).toBeTruthy();
  expect(screen.getByText(/first observed CDR conversion/)).toBeTruthy();
  expect(screen.getByText(/no independently validated/)).toBeTruthy();
  expect(screen.getByText("Synthetic support warning")).toBeTruthy();
});
