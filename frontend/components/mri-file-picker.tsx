"use client";

import { useState } from "react";
import { collectMriAcquisitions, type MriAcquisition } from "@/lib/mri-upload";
import { ErrorState } from "./common";

export function MriFilePicker({
  disabled,
  onSelection,
}: {
  disabled: boolean;
  onSelection: (selection: MriAcquisition | null) => void;
}) {
  const [acquisitions, setAcquisitions] = useState<MriAcquisition[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");
  const selected = acquisitions.find((item) => item.id === selectedId);
  return (
    <div className="mri-file-selection">
      <label>
        MRI files
        <input
          type="file"
          accept=".nii,.nii.gz,.hdr,.img"
          multiple
          required
          disabled={disabled}
          onChange={(event) => {
            const result = collectMriAcquisitions(
              Array.from(event.target.files || []),
            );
            const first = result.acquisitions[0];
            setAcquisitions(result.acquisitions);
            setSelectedId(first?.id || "");
            setError(result.error);
            onSelection(first || null);
          }}
        />
      </label>
      <p>
        For paired MRI, select both files together, such as mpr-1.nifti.hdr and
        mpr-1.nifti.img.
      </p>
      {acquisitions.length > 1 && (
        <label>
          MRI acquisition
          <select
            value={selectedId}
            disabled={disabled}
            onChange={(event) => {
              setSelectedId(event.target.value);
              onSelection(
                acquisitions.find((item) => item.id === event.target.value) ||
                  null,
              );
            }}
          >
            {acquisitions.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      )}
      {selected && (
        <p>
          {selected.kind === "pair"
            ? `${selected.label}: header + image`
            : selected.label}
          {acquisitions.length > 1 &&
            ". Only this acquisition is uploaded for this visit."}
        </p>
      )}
      {error && <ErrorState message={error} />}
    </div>
  );
}
