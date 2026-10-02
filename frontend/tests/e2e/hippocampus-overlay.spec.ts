import { test, expect, type Locator } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import sharp from "sharp";

const env = fs.readFileSync(path.resolve(__dirname, "../../../.env"), "utf8");
const value = (key: string) =>
  env
    .split(/\r?\n/)
    .find((line) => line.startsWith(`${key}=`))
    ?.slice(key.length + 1) || "";

async function yellowBounds(canvas: Locator) {
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

test("patient hippocampus labels rotate, zoom and clip with the MRI", async ({
  page,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  expect(
    (
      await page.request.post("/api/auth/login", {
        data: { email: value("SEED_EMAIL"), password: value("SEED_PASSWORD") },
      })
    ).status(),
  ).toBe(200);
  const jobs = JSON.parse(
    fs.readFileSync(
      path.resolve(
        __dirname,
        "../../../artifacts/experimental-forecast-365-jobs.json",
      ),
      "utf8",
    ),
  );
  await page.setViewportSize({ width: 1536, height: 1100 });
  await page.goto(
    `/patients/${jobs.patients[0].patient_id}?experimentalForecast=365#anatomy-viewer`,
  );
  const section = page.getByRole("region", { name: "3D brain exploration" });
  await section.getByLabel("Hippocampus highlight").check();
  await section.getByLabel("Compare current vs predicted").uncheck();
  await section.getByRole("button", { name: "3D volume", exact: true }).click();
  await expect(section.locator('[data-volume-ready="true"]')).toHaveCount(1, {
    timeout: 60000,
  });
  const canvas = section.locator(".volume-card canvas");
  await section.getByLabel("Camera preset").selectOption("anterior");
  await expect
    .poll(async () => (await yellowBounds(canvas)).count)
    .toBeGreaterThan(100);
  const initial = await yellowBounds(canvas);
  await section.getByLabel("3D zoom", { exact: true }).fill("1.4");
  await expect
    .poll(async () => (await yellowBounds(canvas)).width)
    .toBeGreaterThan(initial.width * 1.15);
  await section.getByLabel("3D zoom", { exact: true }).fill("1");
  await section.getByLabel("Camera preset").selectOption("left");
  await expect
    .poll(async () =>
      Math.abs((await yellowBounds(canvas)).width - initial.width),
    )
    .toBeGreaterThan(5);
  await section.getByLabel("Camera preset").selectOption("anterior");
  const beforeDrag = await yellowBounds(canvas);
  const rect = (await canvas.boundingBox())!;
  await page.mouse.move(rect.x + rect.width / 2, rect.y + rect.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    rect.x + rect.width / 2 + 85,
    rect.y + rect.height / 2 + 45,
    { steps: 8 },
  );
  await page.mouse.up();
  await expect
    .poll(async () => {
      const after = await yellowBounds(canvas);
      return (
        Math.abs(after.width - beforeDrag.width) +
        Math.abs(after.minX - beforeDrag.minX) +
        Math.abs(after.minY - beforeDrag.minY)
      );
    })
    .toBeGreaterThan(8);
  await section.getByLabel("Camera preset").selectOption("oblique");
  await section.getByLabel("Camera preset").selectOption("anterior");
  await section.getByLabel("Cutaway plane").selectOption("coronal");
  await section.getByLabel("Cutaway depth").fill("-0.84");
  const negative = await yellowBounds(canvas);
  await canvas.screenshot({
    path: "test-results/hippocampus-clip-negative.png",
  });
  await section.getByLabel("Cutaway depth").fill("0.84");
  const positive = await yellowBounds(canvas);
  await canvas.screenshot({
    path: "test-results/hippocampus-clip-positive.png",
  });
  expect(Math.min(negative.count, positive.count)).toBeLessThan(
    initial.count * 0.1,
  );
  expect(Math.max(negative.count, positive.count)).toBeGreaterThan(
    initial.count * 0.6,
  );
  await section.getByLabel("Cutaway plane").selectOption("off");
  await expect
    .poll(async () => (await yellowBounds(canvas)).count)
    .toBeGreaterThan(100);
  await section.screenshot({
    path: "test-results/hippocampus-overlay-corrected.png",
  });
  expect(errors).toEqual([]);
});
