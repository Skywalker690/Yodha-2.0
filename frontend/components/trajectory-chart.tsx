"use client";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Result } from "@/types";

export function TrajectoryChart({ result }: { result: Result }) {
  const data = result.visitIds.map((id, i) => ({
    id,
    day: result.daysFromBaseline[i],
    score: Number((result.riskScores[i] * 100).toFixed(2)),
  }));
  return (
    <>
      <div
        className="trajectory-chart"
        role="img"
        aria-label={`Progression-risk estimates: ${data.map((d) => `day ${d.day}: ${d.score}%`).join(", ")}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 20, right: 15, bottom: 10, left: -18 }}
          >
            <defs>
              <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4cd9cb" stopOpacity={0.23} />
                <stop offset="100%" stopColor="#4cd9cb" stopOpacity={0.005} />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="#24313f"
              strokeDasharray="3 5"
              vertical={false}
            />
            <XAxis
              dataKey="day"
              type="number"
              domain={[0, "dataMax"]}
              stroke="#80909f"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `Day ${v}`}
            />
            <YAxis
              stroke="#80909f"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                background: "#162331",
                border: "1px solid #33465b",
                borderRadius: 8,
                color: "#e1eaf4",
                fontSize: 12,
              }}
              labelFormatter={(v) => `Day ${v} from baseline`}
              formatter={(v) => [
                `${Number(v).toFixed(1)}%`,
                "Progression-risk estimate",
              ]}
            />
            <Area
              isAnimationActive={false}
              type="linear"
              dataKey="score"
              stroke="#4cd9cb"
              strokeWidth={2.5}
              fill="url(#riskFill)"
              dot={{ r: 4, strokeWidth: 2, fill: "#132b31" }}
              activeDot={{ r: 6 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-footnote">
        Uncalibrated structural-change index · Percentage does not represent
        disease probability.
      </p>
    </>
  );
}
