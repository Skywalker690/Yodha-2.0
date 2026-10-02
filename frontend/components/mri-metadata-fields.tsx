"use client";

export function MriMetadataFields({
  age,
  nwbv,
  disabled = false,
}: {
  age?: number;
  nwbv?: number;
  disabled?: boolean;
}) {
  return (
    <div className="form-grid mri-metadata-fields">
      <label>
        Age at scan (years)
        <input
          name="age"
          type="number"
          min={18}
          max={120}
          step={1}
          defaultValue={age}
          placeholder="e.g. 72"
          required
          disabled={disabled}
        />
      </label>
      <label>
        nWBV (fraction)
        <input
          name="nwbvFraction"
          type="number"
          min={0}
          max={1}
          step="any"
          defaultValue={nwbv}
          placeholder="e.g. 0.735"
          required
          disabled={disabled}
          onInput={(event) => {
            const input = event.currentTarget;
            input.setCustomValidity(
              Number.isFinite(input.valueAsNumber) && input.valueAsNumber <= 0
                ? "Enter an nWBV fraction greater than 0."
                : "",
            );
          }}
        />
        <span className="muted">
          Normalized whole-brain volume: greater than 0, up to 1.
        </span>
      </label>
    </div>
  );
}
