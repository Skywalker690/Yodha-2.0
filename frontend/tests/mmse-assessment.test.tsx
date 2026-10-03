import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { MMSEAssessment } from "@/components/mmse-assessment";
import { api } from "@/lib/api";
import type { MMSEAssessment as Assessment, Patient, Visit } from "@/types";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));
const tasks = [5, 5, 3, 5, 3, 2, 1, 3, 1, 1, 1].map((maximum, index) => ({
  id: `task-${index}`,
  title: `Task ${index + 1}`,
  max_points: maximum,
  prompt: `Synthetic prompt ${index + 1}`,
  rubric: "Synthetic scoring guide",
}));
const visit = {
  id: "synthetic-visit",
  label: "Baseline",
  metadata: {},
} as Visit;
const patient = { id: "synthetic-patient", source: "uploaded" } as Patient;
const draft: Assessment = {
  id: "synthetic-draft",
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

async function openAssessment(reload = vi.fn()) {
  render(<MMSEAssessment patient={patient} visit={visit} reload={reload} />);
  fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));
  await screen.findByText(tasks[0].prompt);
}

function scoreAll(useZero = false) {
  for (let index = 0; index < tasks.length; index++) {
    const points = useZero ? 0 : tasks[index].max_points;
    fireEvent.click(
      screen.getByRole("radio", {
        name: `${points} ${points === 1 ? "point" : "points"}`,
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: index === tasks.length - 1 ? "Review" : "Next",
      }),
    );
  }
}

it("requires a task score before advancing and accepts administered zero", async () => {
  vi.mocked(api).mockResolvedValueOnce(draft);
  await openAssessment();
  const next = screen.getByRole("button", { name: "Next" });
  expect(next).toBeDisabled();
  expect(
    screen.getByText(/Select the points earned to continue/),
  ).toBeVisible();
  fireEvent.click(next);
  expect(screen.getByText(tasks[0].prompt)).toBeVisible();
  fireEvent.click(screen.getByRole("radio", { name: "0 points" }));
  expect(next).toBeEnabled();
  fireEvent.click(next);
  expect(screen.getByText(tasks[1].prompt)).toBeVisible();
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
});

it.each([false, true])(
  "completes all eleven tasks with zero=%s",
  async (useZero) => {
    const reload = vi.fn();
    vi.mocked(api)
      .mockResolvedValueOnce(draft)
      .mockResolvedValueOnce({ ...draft, revision: 1 })
      .mockResolvedValueOnce({
        ...draft,
        revision: 2,
        status: "completed",
        total: useZero ? 0 : 30,
      });
    await openAssessment(reload);
    scoreAll(useZero);
    expect(
      screen.getByText(
        `Calculated preview: ${useZero ? 0 : 30}/30. The backend verifies the final total.`,
      ),
    ).toBeVisible();
    const complete = screen.getByRole("button", {
      name: "Complete assessment",
    });
    expect(complete).toBeEnabled();
    fireEvent.click(complete);
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    const body = JSON.parse(vi.mocked(api).mock.calls[1][1]!.body as string);
    expect(body.items).toHaveLength(11);
    expect(body).not.toHaveProperty("total");
    expect(vi.mocked(api).mock.calls[1][1]!.method).toBe("PATCH");
    expect(vi.mocked(api).mock.calls[2][0]).toBe(
      "/visits/synthetic-visit/mmse/synthetic-draft/complete",
    );
    expect(JSON.parse(vi.mocked(api).mock.calls[2][1]!.body as string)).toEqual(
      { revision: 1 },
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  },
);

it("preserves completion edits and uses the saved revision when retrying a failed completion", async () => {
  const reload = vi.fn();
  vi.mocked(api)
    .mockResolvedValueOnce(draft)
    .mockResolvedValueOnce({ ...draft, revision: 1 })
    .mockRejectedValueOnce(new Error("Temporary completion failure"))
    .mockResolvedValueOnce({ ...draft, revision: 2 })
    .mockResolvedValueOnce({
      ...draft,
      revision: 3,
      status: "completed",
      total: 30,
    });
  await openAssessment(reload);
  scoreAll();
  fireEvent.click(screen.getByRole("button", { name: "Complete assessment" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Temporary completion failure",
  );
  expect(reload).not.toHaveBeenCalled();
  expect(screen.getByText(/Calculated preview: 30\/30/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Complete assessment" }));
  await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
  expect(
    JSON.parse(vi.mocked(api).mock.calls[3][1]!.body as string).revision,
  ).toBe(1);
});

it("saves unanswered tasks as null and resumes at the first missing score", async () => {
  const partial = { ...draft, revision: 1, items: { "task-0": 0 } };
  const reload = vi.fn();
  vi.mocked(api)
    .mockResolvedValueOnce(draft)
    .mockResolvedValueOnce(partial)
    .mockResolvedValueOnce(partial);
  await openAssessment(reload);
  fireEvent.click(screen.getByRole("radio", { name: "0 points" }));
  fireEvent.click(screen.getByRole("button", { name: "Save draft & close" }));
  await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
  const saved = JSON.parse(vi.mocked(api).mock.calls[1][1]!.body as string);
  expect(saved.items[0].points).toBe(0);
  expect(saved.items[1].points).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));
  await screen.findByText(tasks[1].prompt);
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
});
