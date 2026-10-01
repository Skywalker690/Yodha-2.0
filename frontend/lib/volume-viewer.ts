import type { Niivue } from "@niivue/niivue";

export type VolumeLayout =
  "render" | "multiplanar" | "axial" | "coronal" | "sagittal";
export type ClipAxis = "off" | "axial" | "coronal" | "sagittal";
export type CameraPreset =
  "oblique" | "anterior" | "posterior" | "left" | "right" | "superior";

export const CAMERA_PRESETS: Record<CameraPreset, [number, number]> = {
  oblique: [125, 20],
  anterior: [180, 0],
  posterior: [0, 0],
  left: [90, 0],
  right: [270, 0],
  superior: [0, 90],
};

export function clipPlane(axis: ClipAxis, depth: number): number[] {
  if (axis === "off") return [2, 0, 0];
  const angles: Record<Exclude<ClipAxis, "off">, [number, number]> = {
    axial: [0, 90],
    coronal: [0, 0],
    sagittal: [90, 0],
  };
  return [Math.max(-1, Math.min(1, depth)), ...angles[axis]];
}

export async function fetchVolume(
  url: string,
  signal: AbortSignal,
): Promise<{ buffer: ArrayBuffer; name: string }> {
  if (!url.startsWith("/api/") || url.includes(".."))
    throw new Error("Invalid local volume URL.");
  const response = await fetch(url, {
    signal,
    credentials: "same-origin",
    cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 401)
      throw new Error("Session expired. Sign in again to view this scan.");
    if (response.status === 404)
      throw new Error(
        "Volume unavailable. For 3D differences, run local inference again.",
      );
    throw new Error("The local service could not load this MRI volume.");
  }
  const limit = 100 * 1024 * 1024;
  const length = Number(response.headers.get("content-length"));
  if (length > limit)
    throw new Error("Volume exceeds the browser loading limit.");
  const buffer = await response.arrayBuffer();
  if (!buffer.byteLength || buffer.byteLength > limit)
    throw new Error("Invalid or oversized MRI volume.");
  const bytes = new Uint8Array(buffer);
  return {
    buffer,
    name: bytes[0] === 31 && bytes[1] === 139 ? "volume.nii.gz" : "volume.nii",
  };
}

export function releaseViewer(viewer: Niivue): void {
  viewer.broadcastTo([], { "2d": false, "3d": false });
  viewer.onLocationChange = () => {};
  viewer.cleanup();
  viewer.volumes = [];
  viewer.meshes = [];
  // Failed WebGL initialization can leave Niivue without its throwing `gl` getter.
  const gl = viewer.canvas?.getContext("webgl2");
  gl?.getExtension("WEBGL_lose_context")?.loseContext();
}

export function applyVolumeAppearance(
  viewer: Niivue,
  range: [number, number],
  settings: {
    lower: number;
    upper: number;
    colormap: string;
    opacity: number;
    overlayOpacity: number;
    differenceThreshold: number;
  },
): void {
  const volume = viewer.volumes[0];
  if (!volume) return;
  // NiiVue's setColormap recalibrates intensity. Apply our window AFTER it.
  if (volume.colormap !== settings.colormap)
    volume.setColormap(settings.colormap);
  const [low, high] = range;
  volume.cal_min = low + ((high - low) * settings.lower) / 100;
  volume.cal_max = low + ((high - low) * settings.upper) / 100;
  volume.opacity = settings.opacity;
  const difference = viewer.volumes[1];
  if (difference) {
    if (difference.colormap !== "warm") difference.setColormap("warm");
    difference.colormapType = 0; // MIN_TO_MAX; sub-threshold voxels use the transparent LUT origin.
    difference.cal_min = settings.differenceThreshold;
    difference.cal_max = 0.3;
    difference.colorbarVisible = false;
    difference.opacity = settings.overlayOpacity;
  }
  viewer.updateGLVolume();
}

export async function saveResearchSnapshot(
  viewer: Niivue,
  filename: string,
  caption: string,
): Promise<void> {
  viewer.drawScene();
  const source = viewer.canvas;
  if (!source) throw new Error("The viewer is not ready for a snapshot.");
  const output = document.createElement("canvas");
  output.width = source.width;
  output.height = source.height + 72;
  const context = output.getContext("2d");
  if (!context)
    throw new Error("Snapshot export is not supported by this browser.");
  context.fillStyle = "#0b1420";
  context.fillRect(0, 0, output.width, output.height);
  context.drawImage(source, 0, 0);
  context.fillStyle = "#dceaf3";
  context.font = `${Math.max(12, Math.round(output.width / 85))}px sans-serif`;
  context.fillText(caption, 16, source.height + 25, output.width - 32);
  context.fillStyle = "#62d9cf";
  context.fillText(
    "Research visualization | Not a medical diagnosis | Not registered anatomy",
    16,
    source.height + 50,
    output.width - 32,
  );
  const blob = await new Promise<Blob>((resolve, reject) =>
    output.toBlob(
      (value) =>
        value ? resolve(value) : reject(new Error("Snapshot export failed.")),
      "image/png",
    ),
  );
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
