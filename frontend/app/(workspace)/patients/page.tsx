"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState, Loading, PageTitle } from "@/components/common";
import { PatientTable } from "@/components/patient-table";
import { MriMetadataFields } from "@/components/mri-metadata-fields";
import { useResource } from "@/lib/use-resource";
import { post } from "@/lib/api";
import type { Patient } from "@/types";

const PRIORITY_PATIENT_CODES = [
  "OAS2_0048",
  "OAS2_0070",
  "OAS2_0073",
  "OAS2_0127",
  "OAS2_0017",
];
const patientPriority = new Map(
  PRIORITY_PATIENT_CODES.map((code, index) => [code, index]),
);

export default function Patients() {
  const { data, loading, error, reload } = useResource<Patient[]>(
    "/patients",
    5000,
  );
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");
  const router = useRouter();
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("new") === "1")
      setShowForm(true);
  }, []);
  return (
    <>
      <PageTitle
        eyebrow="YOUR RESEARCH COHORT"
        title="Patients"
        action={
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus size={16} /> Add patient
          </Button>
        }
      >
        Organize subjects, connect visits, and follow their research journey.
      </PageTitle>
      {showForm && (
        <section className="panel form-panel">
          <div className="panel-heading">
            <h2>Create a research patient</h2>
            <button
              aria-label="Close patient form"
              className="icon-button"
              onClick={() => setShowForm(false)}
            >
              <X size={18} />
            </button>
          </div>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (busy) return;
              setBusy(true);
              setFormError("");
              const fd = new FormData(e.currentTarget);
              try {
                const p = await post<Patient>("/patients", {
                  age: Number(fd.get("age")),
                  nwbvFraction: Number(fd.get("nwbvFraction")),
                  sex: fd.get("sex") || null,
                  notes: fd.get("notes"),
                });
                router.push(`/patients/${p.id}`);
              } catch (e) {
                setFormError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <p className="muted">
              Patient code is generated automatically. Age and nWBV are required.
              Upload the baseline MRI on the next screen.
            </p>
            <MriMetadataFields disabled={busy} />
            <div className="form-grid">
              <label>
                Sex (optional)
                <select name="sex" disabled={busy}>
                  <option value="">Unspecified</option>
                  <option>Female</option>
                  <option>Male</option>
                  <option>Other</option>
                </select>
              </label>
            </div>
            <label>
              Research notes (optional)
              <textarea
                name="notes"
                maxLength={1000}
                placeholder="Add context for this research case"
                rows={2}
                disabled={busy}
              />
            </label>
            {formError && <ErrorState message={formError} />}
            <Button disabled={busy}>
              {busy ? "Creating…" : "Create patient"}
            </Button>
          </form>
        </section>
      )}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>
              Patient directory{" "}
              <span className="count-pill">{data?.length || 0}</span>
            </h2>
            <p>All subjects in this local workspace</p>
          </div>
          <label className="search-field">
            <Search size={17} />
            <span className="sr-only">Search patients</span>
            <input
              placeholder="Search patient code…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
        </div>
        {loading ? (
          <Loading />
        ) : error ? (
          <ErrorState message={error} onRetry={reload} />
        ) : (
          <PatientTable
            patients={(data || [])
              .filter((p) => p.code.toLowerCase().includes(query.toLowerCase()))
              .sort(
                (a, b) =>
                  (patientPriority.get(a.code) ?? PRIORITY_PATIENT_CODES.length) -
                  (patientPriority.get(b.code) ?? PRIORITY_PATIENT_CODES.length),
              )}
          />
        )}
      </section>
    </>
  );
}
