import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { useResource } from "@/lib/use-resource";

vi.mock("@/lib/api", () => ({ api: vi.fn() }));

beforeEach(() => vi.mocked(api).mockReset());

it("hides the previous patient while a new resource loads", async () => {
  let resolveNew!: (value: { code: string }) => void;
  vi.mocked(api).mockResolvedValueOnce({ code: "CASE_A" });
  vi.mocked(api).mockReturnValueOnce(
    new Promise((resolve) => {
      resolveNew = resolve;
    }),
  );
  const { result, rerender } = renderHook(
    ({ path }) => useResource<{ code: string }>(path),
    { initialProps: { path: "/patients/a" } },
  );
  await waitFor(() => expect(result.current.data?.code).toBe("CASE_A"));
  rerender({ path: "/patients/b" });
  expect(result.current.data).toBeNull();
  expect(result.current.loading).toBe(true);
  await act(async () => resolveNew({ code: "CASE_B" }));
  expect(result.current.data?.code).toBe("CASE_B");
});

it("ignores a stale response that finishes after a newer selection", async () => {
  let resolveOld!: (value: { code: string }) => void;
  vi.mocked(api).mockReturnValueOnce(
    new Promise((resolve) => {
      resolveOld = resolve;
    }),
  );
  vi.mocked(api).mockResolvedValueOnce({ code: "CASE_B" });
  const { result, rerender } = renderHook(
    ({ path }) => useResource<{ code: string }>(path),
    { initialProps: { path: "/patients/a" } },
  );
  rerender({ path: "/patients/b" });
  await waitFor(() => expect(result.current.data?.code).toBe("CASE_B"));
  await act(async () => resolveOld({ code: "CASE_A" }));
  expect(result.current.data?.code).toBe("CASE_B");
});

it("does not overlap polling requests or discard a slow service error", async () => {
  let rejectRequest!: (error: Error) => void;
  vi.mocked(api).mockReturnValueOnce(
    new Promise((_resolve, reject) => {
      rejectRequest = reject;
    }),
  );
  const { result } = renderHook(() => useResource("/patients"));
  await act(async () => {
    await result.current.reload();
  });
  expect(api).toHaveBeenCalledTimes(1);
  await act(async () => rejectRequest(new Error("Local service unavailable")));
  expect(result.current.loading).toBe(false);
  expect(result.current.error).toBe("Local service unavailable");
});
