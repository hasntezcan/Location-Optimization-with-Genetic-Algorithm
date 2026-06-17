"use client";

import { useCallback, useRef, useState } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import {
  CartesianGrid,
  Cell,
  Line,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { ChartPoint } from "@/lib/chart-data";

export type ArchiveComparisonChartProps = {
  chartData: ChartPoint[];
  paretoLineData: ChartPoint[];
  onSelectSolutionId: (id: number) => void;
  title?: string;
  className?: string;
  chartClassName?: string;
  showLegend?: boolean;
  showFocusButton?: boolean;
  isFocusMode?: boolean;
  onToggleFocusMode?: () => void;
};

export function ArchiveComparisonChart({
  chartData,
  paretoLineData,
  onSelectSolutionId,
  title = "Alternatif karşılaştırması",
  className = "",
  chartClassName = "min-h-[210px]",
  showLegend = true,
  showFocusButton = false,
  isFocusMode = false,
  onToggleFocusMode,
}: ArchiveComparisonChartProps) {
  const chartObserverRef = useRef<ResizeObserver | null>(null);
  const [chartSize, setChartSize] = useState({ width: 0, height: 0 });
  const isChartReady = chartSize.width > 80 && chartSize.height > 80;

  const chartContainerRef = useCallback((element: HTMLDivElement | null) => {
    chartObserverRef.current?.disconnect();
    chartObserverRef.current = null;

    if (!element) return;

    const updateSize = (width: number, height: number) => {
      setChartSize({
        width: Math.max(0, Math.floor(width)),
        height: Math.max(0, Math.floor(height)),
      });
    };

    const rect = element.getBoundingClientRect();
    updateSize(rect.width, rect.height);

    if (typeof ResizeObserver === "undefined") return;

    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return;
      updateSize(entry.contentRect.width, entry.contentRect.height);
    });

    observer.observe(element);
    chartObserverRef.current = observer;
  }, []);

  return (
    <div className={`flex h-full flex-col ${className}`}>
      <div className="mb-2 flex items-start justify-between gap-1">
        <span className="shrink-0 text-[10px] font-bold uppercase leading-5 tracking-widest text-slate-400">
          {title}
        </span>
        <div className="flex flex-wrap items-center justify-end gap-x-2 gap-y-1">
          {showLegend ? (
            <>
              <div className="flex items-center gap-1">
                <div className="h-0.5 w-2 border-t border-dashed border-indigo-400 bg-indigo-400" />
                <span className="text-[9px] text-slate-500">Alternatifler</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-blue-500" />
                <span className="text-[9px] text-slate-500">Yakınlık</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-emerald-600" />
                <span className="text-[9px] text-slate-500">Denge</span>
              </div>
            </>
          ) : null}
          {showFocusButton && onToggleFocusMode ? (
            <button
              type="button"
              onClick={onToggleFocusMode}
              className="hidden h-6 w-6 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:border-indigo-300 hover:bg-slate-50 hover:text-indigo-600 lg:flex"
              aria-label={isFocusMode ? "Odak modundan çık" : "Odak moduna gir"}
              title={isFocusMode ? "Odak modundan çık" : "Odak modu"}
            >
              {isFocusMode ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
            </button>
          ) : null}
        </div>
      </div>

      <div
        ref={chartContainerRef}
        className={`min-w-0 flex-1 focus:outline-none [&_*]:focus:outline-none [&_.recharts-surface]:focus:outline-none [&_.recharts-wrapper]:focus:outline-none ${chartClassName}`}
      >
        {chartData.length > 0 && isChartReady ? (
          <ScatterChart
            width={chartSize.width}
            height={chartSize.height}
            margin={{ top: 10, right: 20, bottom: 20, left: -10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              type="number"
              dataKey="x"
              name="Müşteriye Yakınlık"
              unit=""
              fontSize={10}
              domain={["auto", "auto"]}
              tickCount={5}
              label={{
                value: "Müşteriye Yakınlık",
                position: "insideBottom",
                offset: -10,
                fontSize: 10,
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Bölgesel Denge"
              unit=""
              fontSize={10}
              domain={["auto", "auto"]}
              tickCount={5}
              label={{
                value: "Bölgesel Denge",
                angle: -90,
                position: "insideLeft",
                offset: 10,
                fontSize: 10,
              }}
            />
            <ZAxis type="number" dataKey="size" range={[50, 400]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload as ChartPoint;
                  return (
                    <div className="rounded-lg border border-slate-200 bg-white p-2 text-[10px] shadow-md">
                      <div className="mb-1 flex items-center justify-between gap-4">
                        <p className="font-bold">Öneri No #{data.id + 1}</p>
                        {data.isSelected ? (
                          <span className="rounded bg-slate-900 px-1 text-[8px] text-white">
                            SEÇİLİ
                          </span>
                        ) : null}
                      </div>
                      <p>Müşteriye yakınlık: {data.x.toFixed(4)}</p>
                      <p>Bölgesel denge: {data.y.toFixed(4)}</p>
                      {data.isBestF1 ? (
                        <p className="font-bold text-blue-500">Yakınlık odaklı</p>
                      ) : null}
                      {data.isBestF2 ? (
                        <p className="font-bold text-emerald-600">Denge odaklı</p>
                      ) : null}
                      {data.isPareto ? (
                        <p className="text-emerald-500">Öne çıkan alternatif</p>
                      ) : null}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Line
              type="monotone"
              data={paretoLineData}
              dataKey="y"
              stroke="#818cf8"
              strokeDasharray="5 5"
              dot={false}
              activeDot={false}
              legendType="none"
              connectNulls
            />
            <Scatter
              name="Öneriler"
              data={chartData}
              onClick={(data: unknown) => {
                const id = (data as Partial<ChartPoint> | null)?.id;
                if (typeof id === "number") onSelectSolutionId(id);
              }}
            >
              {chartData.map((entry, index) => {
                let fill = "#94a3b8";
                let stroke = "none";
                let strokeWidth = 0;

                if (entry.isSelected) {
                  stroke = "#0f172a";
                  strokeWidth = 3;
                }

                if (entry.isBestF1) fill = "#3b82f6";
                else if (entry.isBestF2) fill = "#059669";
                else if (entry.isPareto) fill = "#10b981";

                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={strokeWidth}
                    className={`cursor-pointer transition-all duration-200 hover:opacity-80 ${
                      entry.isSelected ? "animate-pulse" : ""
                    }`}
                  />
                );
              })}
            </Scatter>
          </ScatterChart>
        ) : (
          <div className="flex h-full min-h-[180px] items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 text-center text-xs text-slate-500">
            {chartData.length > 0
              ? "Karşılaştırma hazırlanıyor..."
              : "Alternatif konum önerilerini görmek için önce önerileri oluşturun."}
          </div>
        )}
      </div>
    </div>
  );
}
