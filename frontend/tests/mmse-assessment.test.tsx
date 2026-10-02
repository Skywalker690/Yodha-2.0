import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { MMSEAssessment } from "@/components/mmse-assessment";
import { PatientValuesPanel } from "@/components/patient-values-panel";
import { api } from "@/lib/api";
import type { MMSEAssessment as Assessment, Patient, Visit } from "@/types";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));
const tasks = [5, 5, 3, 5, 3, 2, 1, 3, 1, 1, 1].map((maximum, index) => ({
  id: `task-${index}`,
  title: `Task ${index + 1}`,
  max_points: maximum,
  prompt: `Synthetic task prompt ${index + 1}`,
  rubric: "Synthetic clinician scoring guide",
}));
const visit = {
  id: "visit-a",
  label: "Baseline",
  metadata: {},
  hasMri: false,
} as Visit;
const patient = {
  id: "patient-a",
  code: "SYNTHETIC",
  source: "uploaded",
  visits: [visit],
  age: 72,
  sex: "Female",
} as Patient;
const draft: Assessment = {
  id: "draft-a",
  status: "draft",
  revision: 0,
  instrument: "alzhio-cognitive-demo",
  version: "synthetic-v1",
  language: "English",
  assessedAt: "2026-10-01T12:00:00Z",
  total: null,
  items: {},
  definition: { items: tasks },
};
beforeEach(() => vi.mocked(api).mockReset());

it("completes task recording without sending a total and keeps demo labeling visible", async () => {
  const reload = vi.fn();
  vi.mocked(api)
    .mockResolvedValueOnce(draft)
    .mockResolvedValueOnce({ ...draft, revision: 1 })
    .mockResolvedValueOnce({
      ...draft,
      revision: 2,
      status: "completed",
      total: 30,
    });
  render(<MMSEAssessment patient={patient} visit={visit} reload={reload} />);
  fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));
  await screen.findByRole("heading", { name: "MMSE-style demo" });
  expect(screen.getByText(/not a standardized MMSE/)).toBeVisible();
  expect(
    screen.queryByRole("radio", { name: "Not administered" }),
  ).not.toBeInTheDocument();
  for (let index = 0; index < tasks.length; index++) {
    const maximum = tasks[index].max_points;
    fireEvent.click(
      screen.getByRole("radio", {
        name: `${maximum} ${maximum === 1 ? "point" : "points"}`,
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: index === tasks.length - 1 ? "Review" : "Next",
      }),
    );
  }
  expect(screen.getByText(/Calculated preview: 30\/30/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Complete assessment" }));
  await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
  const saved = JSON.parse(vi.mocked(api).mock.calls[1][1]!.body as string);
  expect(saved.items).toHaveLength(11);
  expect(saved).not.toHaveProperty("total");
  expect(vi.mocked(api).mock.calls[1][0]).toBe("/visits/visit-a/mmse/draft-a");
  expect(vi.mocked(api).mock.calls[2][0]).toBe(
    "/visits/visit-a/mmse/draft-a/complete",
  );
  expect(JSON.parse(vi.mocked(api).mock.calls[2][1]!.body as string)).toEqual({
    revision: 1,
  });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("polling preserves unsaved task results and saves unadministered tasks as null", async () => {
  vi.mocked(api)
    .mockResolvedValueOnce(draft)
    .mockResolvedValueOnce({ ...draft, revision: 1 });
  const reload = vi.fn();
  const { rerender } = render(
    <MMSEAssessment patient={patient} visit={visit} reload={reload} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));
  await screen.findByText(tasks[0].prompt);
  fireEvent.click(screen.getByRole("radio", { name: "3 points" }));
  rerender(
    <MMSEAssessment
      patient={{ ...patient }}
      visit={{ ...visit }}
      reload={reload}
    />,
  );
  expect(screen.getByRole("radio", { name: "3 points" })).toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Save draft & close" }));
  await waitFor(() => expect(reload).toHaveBeenCalled());
  const body = JSON.parse(vi.mocked(api).mock.calls[1][1]!.body as string);
  expect(body.items[0].points).toBe(3);
  expect(body.items[1].points).toBeNull();
  expect(vi.mocked(api)).toHaveBeenCalledTimes(2);
});

it("an incomplete assessment cannot complete and a failed save preserves edits", async () => {
  vi.mocked(api)
    .mockResolvedValueOnce(draft)
    .mockRejectedValueOnce(new Error("Draft changed in another session"));
  render(<MMSEAssessment patient={patient} visit={visit} reload={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));
  await screen.findByText(tasks[0].prompt);
  fireEvent.click(screen.getByRole("radio", { name: "0 points" }));
  fireEvent.click(screen.getByRole("button", { name: "Save draft & close" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Draft changed");
  expect(screen.getByRole("radio", { name: "0 points" })).toBeChecked();
  for (let index = 0; index < tasks.length; index++) {
    fireEvent.click(
      screen.getByRole("button", {
        name: index === tasks.length - 1 ? "Review" : "Next",
      }),
    );
  }
  expect(
    screen.getByRole("button", { name: "Complete assessment" }),
  ).toBeDisabled();
});

it("patient/visit unmount aborts late requests", async () => {
  let resolve!: (value: Assessment) => void;
  vi.mocked(api).mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done as typeof resolve;
      }),
  );
  const { unmount } = render(
    <MMSEAssessment patient={patient} visit={visit} reload={vi.fn()} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));
  const signal = vi.mocked(api).mock.calls[0][1]?.signal;
  unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => resolve(draft));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("shows clinical and separate demo scores before anatomy processing and preserves imported cases", () => {
  const observedVisit = {
    ...visit,
    metadata: { MMSE: 24, cognitiveDemoScore: 27 },
  };
  const observedPatient = { ...patient, visits: [observedVisit] };
  render(<PatientValuesPanel patients={[observedPatient]} />);
  expect(screen.getByText("24")).toBeVisible();
  expect(screen.getByText("27")).toBeVisible();
  expect(screen.getByText("demo · /30 · not MMSE")).toBeVisible();
  render(
    <MMSEAssessment
      patient={{ ...patient, source: "oasis-2" }}
      visit={observedVisit}
      reload={vi.fn()}
    />,
  );
  expect(screen.getByText("Recorded MMSE: 24/30")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Start assessment" }),
  ).not.toBeInTheDocument();
});
