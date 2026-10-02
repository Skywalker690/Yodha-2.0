import type { Locator } from "@playwright/test";
import sharp from "sharp";

export async function yellowBounds(canvas: Locator) {
  const { data, info } = await sharp(await canvas.screenshot())
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  let count = 0;
  let minX = info.width,
    maxX = 0,
    minY = info.height,
    maxY = 0;
  for (let y = 0; y < info.height; y++) {
    for (let x = 0; x < info.width; x++) {
      const index = (y * info.width + x) * info.channels;
      const [r, g, b] = [data[index], data[index + 1], data[index + 2]];
      if (
        r > 60 &&
        g > 60 &&
        b < Math.min(r, g) * 0.6 &&
        Math.abs(r - g) < 70
      ) {
        count++;
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
    }
  }
  return {
    count,
    width: count ? maxX - minX + 1 : 0,
    height: count ? maxY - minY + 1 : 0,
    minX,
    minY,
  };
}
