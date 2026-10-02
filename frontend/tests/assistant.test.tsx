import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ClinicalAssistant } from "@/components/clinical-assistant";
import { api } from "@/lib/api";
import type { AssistantResponse, Patient } from "@/types";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));

const patient = {
  id: "patient-a",
  visits: [{ id: "v1" }, { id: "v2" }, { id: "v3" }],
} as Patient;
const response: AssistantResponse = {
  answer: "Observed MMSE decreased across visits.",
  sources: [
    {
      title: "Research source",
      url: "https://pubmed.ncbi.nlm.nih.gov/1/",
      supportedText: ["MRI supports structural assessment."],
    },
  ],
  searchSuggestions: "<div>Search suggestions</div>",
  researchRequested: true,
  contextSummary: {
    visitCount: 3,
    clinicalFieldsUsed: ["MMSE", "CDR"],
    anatomyIncluded: true,
    anatomyReviewed: false,
    forecastIncluded: false,
    rawMriSent: false,
  },
  model: "gemini-test",
  disclaimer:
    "For clinician review; not a diagnosis or treatment recommendation.",
};

beforeEach(() => vi.mocked(api).mockReset());

function openAssistant() {
  fireEvent.click(screen.getByRole("button", { name: "Clinical Assistant" }));
}

it("sends bounded history, survives patient polling, and shows supported research references", async () => {
  vi.mocked(api).mockResolvedValue(response);
  const { rerender } = render(<ClinicalAssistant patient={patient} />);
  openAssistant();
  fireEvent.click(screen.getByRole("button", { name: "Explore research" }));
  await screen.findByText(response.answer);
  expect(api).toHaveBeenCalledWith(
    "/patients/patient-a/assistant",
    expect.objectContaining({
      body: expect.stringContaining('"useResearchSources":true'),
    }),
  );
  fireEvent.click(screen.getByText("Web references (1)"));
  expect(screen.getByRole("link", { name: /Research source/ })).toHaveAttribute(
    "href",
    response.sources[0].url,
  );
  expect(screen.getByText("MRI supports structural assessment.")).toBeVisible();
  expect(screen.getByTitle("Google Search suggestions")).toHaveAttribute(
    "sandbox",
    "allow-popups allow-popups-to-escape-sandbox",
  );
  rerender(<ClinicalAssistant patient={{ ...patient }} />);
  expect(screen.getByText(response.answer)).toBeVisible();
  fireEvent.change(screen.getByLabelText("Ask about this patient"), {
    target: { value: "What changed?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  await waitFor(() => expect(api).toHaveBeenCalledTimes(2));
  const body = JSON.parse(vi.mocked(api).mock.calls[1][1]!.body as string);
  expect(body.history).toHaveLength(2);
  expect(body.history[1]).toEqual({
    role: "assistant",
    content: response.answer,
  });
});

it("preserves the question after failure and retries without duplicating a failed turn", async () => {
  vi.mocked(api).mockRejectedValueOnce(new Error("Configure GEMINI_API_KEY"));
  vi.mocked(api).mockResolvedValueOnce(response);
  render(<ClinicalAssistant patient={patient} />);
  openAssistant();
  fireEvent.change(screen.getByLabelText("Ask about this patient"), {
    target: { value: "Summarize" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Configure GEMINI_API_KEY",
  );
  expect(screen.getByLabelText("Ask about this patient")).toHaveValue(
    "Summarize",
  );
  fireEvent.click(screen.getByRole("button", { name: "Retry question" }));
  await screen.findByText(response.answer);
  expect(
    JSON.parse(vi.mocked(api).mock.calls[1][1]!.body as string).history,
  ).toEqual([]);
  expect(screen.getAllByText("Summarize")).toHaveLength(1);
});

it("aborts late replies when switching patients and clears conversation", async () => {
  let resolve!: (data: AssistantResponse) => void;
  vi.mocked(api).mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const { rerender } = render(<ClinicalAssistant patient={patient} />);
  openAssistant();
  fireEvent.click(screen.getByRole("button", { name: "Summarize the case" }));
  const signal = vi.mocked(api).mock.calls[0][1]!.signal;
  rerender(<ClinicalAssistant patient={{ ...patient, id: "patient-b" }} />);
  expect(signal?.aborted).toBe(true);
  await act(async () => resolve(response));
  expect(screen.queryByText(response.answer)).toBeNull();
  expect(screen.queryByRole("log")).toBeNull();
});

it("displays an explicit empty-source state and clears completed messages", async () => {
  vi.mocked(api).mockResolvedValue({
    ...response,
    sources: [],
    searchSuggestions: null,
  });
  render(<ClinicalAssistant patient={patient} />);
  openAssistant();
  expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Explore research" }));
  await screen.findByText("No web references were returned for this response.");
  fireEvent.click(screen.getByRole("button", { name: "Clear" }));
  expect(screen.queryByRole("log")).toBeNull();
});

it("keeps the chat out of the workspace until its widget is opened", () => {
  render(<ClinicalAssistant patient={patient} />);
  expect(screen.queryByRole("dialog")).toBeNull();
  openAssistant();
  expect(screen.getByRole("dialog")).toBeVisible();
  fireEvent.click(
    screen.getByRole("button", { name: "Close Clinical Assistant" }),
  );
  expect(screen.queryByRole("dialog")).toBeNull();
});
