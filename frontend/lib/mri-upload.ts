export type MriAcquisition =
  | { id: string; label: string; kind: "volume"; file: File }
  | { id: string; label: string; kind: "pair"; header: File; image: File };

const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

export function collectMriAcquisitions(files: File[]): {
  acquisitions: MriAcquisition[];
  error: string;
} {
  const invalid = (error: string) => ({ acquisitions: [], error });
  if (!files.length) return invalid("");
  if (files.length === 1 && /\.nii(\.gz)?$/i.test(files[0].name)) {
    const file = files[0];
    if (file.size > MAX_UPLOAD_BYTES)
      return invalid("The MRI volume exceeds 100 MiB.");
    return {
      acquisitions: [{ id: file.name, label: file.name, kind: "volume", file }],
      error: "",
    };
  }
  const pairs = new Map<
    string,
    { label: string; header?: File; image?: File }
  >();
  for (const file of files) {
    const match = file.name.match(/^(.+)\.(hdr|img)$/i);
    if (!match)
      return invalid(
        "Choose one .nii/.nii.gz volume or matching .hdr/.img pairs without mixing formats.",
      );
    const id = match[1].toLowerCase();
    const pair = pairs.get(id) || { label: match[1] };
    const partner = match[2].toLowerCase() === "hdr" ? "header" : "image";
    if (pair[partner])
      return invalid(
        `More than one ${match[2]} file was selected for ${pair.label}.`,
      );
    pair[partner] = file;
    pairs.set(id, pair);
  }
  const acquisitions: MriAcquisition[] = [];
  for (const [id, { label, header, image }] of pairs) {
    if (!header || !image)
      return invalid(`Select both ${label}.hdr and ${label}.img together.`);
    if (header.size + image.size > MAX_UPLOAD_BYTES)
      return invalid(`The ${label} pair exceeds the combined 100 MiB limit.`);
    acquisitions.push({ id, label, kind: "pair", header, image });
  }
  acquisitions.sort((a, b) => {
    const priority = (label: string) => (/^mpr-1(?:\.|$)/i.test(label) ? 0 : 1);
    return (
      priority(a.label) - priority(b.label) ||
      a.label.localeCompare(b.label, undefined, { numeric: true })
    );
  });
  return { acquisitions, error: "" };
}
