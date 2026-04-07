import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Image as ImageIcon, RefreshCcw, Video } from "lucide-react";

import Layout from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useAuth } from "@/lib/auth";
import {
  CameraListResponse,
  DetectionListResponse,
  VisitorType,
  getMediaUrl,
  readApiError,
} from "@/lib/api";

const PAGE_SIZE = 15;

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString();
}

export default function History() {
  const { authFetch } = useAuth();
  const [page, setPage] = useState(1);
  const [plateFilter, setPlateFilter] = useState("");
  const [visitorType, setVisitorType] = useState<VisitorType | "ALL">("ALL");
  const [cameraId, setCameraId] = useState("ALL");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const deferredPlateFilter = useDeferredValue(plateFilter);
  const debouncedPlateFilter = useDebouncedValue(deferredPlateFilter, 300);

  useEffect(() => {
    setPage(1);
  }, [cameraId, debouncedPlateFilter, fromDate, toDate, visitorType]);

  const cameraQuery = useQuery({
    queryKey: ["history-cameras"],
    queryFn: async () => {
      const response = await authFetch("/cameras");
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return (await response.json()) as CameraListResponse;
    },
  });

  const historyQuery = useQuery({
    queryKey: [
      "history",
      page,
      debouncedPlateFilter,
      visitorType,
      cameraId,
      fromDate,
      toDate,
    ],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: `${page}`,
        page_size: `${PAGE_SIZE}`,
      });

      if (debouncedPlateFilter) {
        params.set("plate", debouncedPlateFilter);
      }
      if (visitorType !== "ALL") {
        params.set("visitor_type", visitorType);
      }
      if (cameraId !== "ALL") {
        params.set("camera_id", cameraId);
      }
      if (fromDate) {
        params.set("from", new Date(fromDate).toISOString());
      }
      if (toDate) {
        params.set("to", new Date(toDate).toISOString());
      }

      const response = await authFetch(`/detections?${params.toString()}`);
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return (await response.json()) as DetectionListResponse;
    },
  });

  const totalPages = useMemo(() => {
    const total = historyQuery.data?.pagination.total ?? 0;
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }, [historyQuery.data?.pagination.total]);

  return (
    <Layout
      subtitle="Search and audit stored detections without adding dashboard noise."
      title="Detections History"
      actions={
        <Button
          onClick={() => historyQuery.refetch()}
          size="sm"
          type="button"
          variant="outline"
        >
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </Button>
      }
    >
      <section className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
        <div className="grid gap-3 xl:grid-cols-[1.3fr_180px_180px_220px_220px]">
          <Input
            onChange={(event) => setPlateFilter(event.target.value)}
            placeholder="Filter by plate number"
            value={plateFilter}
          />

          <select
            className="flex h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground"
            onChange={(event) =>
              setVisitorType(event.target.value as VisitorType | "ALL")
            }
            value={visitorType}
          >
            <option value="ALL">All visitor types</option>
            <option value="CITIZEN">CITIZEN</option>
            <option value="GUEST">GUEST</option>
            <option value="BANNED">BANNED</option>
          </select>

          <select
            className="flex h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground"
            onChange={(event) => setCameraId(event.target.value)}
            value={cameraId}
          >
            <option value="ALL">All cameras</option>
            {cameraQuery.data?.items.map((camera) => (
              <option key={camera.id} value={camera.id}>
                {camera.location_name}
              </option>
            ))}
          </select>

          <Input
            onChange={(event) => setFromDate(event.target.value)}
            type="datetime-local"
            value={fromDate}
          />

          <Input
            onChange={(event) => setToDate(event.target.value)}
            type="datetime-local"
            value={toDate}
          />
        </div>

        <div className="mt-5 overflow-hidden rounded-2xl border border-border">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px]">
              <thead className="bg-background/80">
                <tr className="text-left text-xs uppercase tracking-[0.24em] text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Capture</th>
                  <th className="px-4 py-3 font-medium">Plate</th>
                  <th className="px-4 py-3 font-medium">Visitor type</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Camera</th>
                  <th className="px-4 py-3 font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {historyQuery.data?.items.map((detection) => (
                  <tr
                    className="border-t border-border/80 text-sm text-foreground"
                    key={detection.id}
                  >
                    <td className="px-4 py-4">
                      {detection.capture_url ? (
                        <div className="group relative h-16 w-28 overflow-hidden rounded-xl border border-border bg-background/60">
                          <img
                            alt={`Detection ${detection.plate_number}`}
                            className="h-full w-full object-cover transition duration-200 group-hover:scale-105"
                            src={getMediaUrl(detection.capture_url) ?? undefined}
                          />
                          <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-slate-950/95 via-slate-950/60 to-transparent px-2 pb-2 pt-6 text-[10px] uppercase tracking-[0.2em] text-slate-200">
                            <span className="truncate">
                              {detection.input_kind}
                            </span>
                            {detection.input_kind === "video" ? (
                              <Video className="h-3.5 w-3.5" />
                            ) : (
                              <ImageIcon className="h-3.5 w-3.5" />
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="flex h-16 w-28 items-center justify-center rounded-xl border border-border bg-background/40 text-muted-foreground">
                          <ImageIcon className="h-4 w-4" />
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4 font-mono text-base">
                      {detection.plate_number}
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge value={detection.visitor_type} />
                    </td>
                    <td className="px-4 py-4">
                      {(detection.confidence * 100).toFixed(2)}%
                    </td>
                    <td className="px-4 py-4">{detection.camera_name}</td>
                    <td className="px-4 py-4 text-muted-foreground">
                      {formatTimestamp(detection.timestamp)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {historyQuery.isLoading && (
            <div className="px-4 py-10 text-center text-sm text-muted-foreground">
              Loading detections history...
            </div>
          )}

          {!historyQuery.isLoading && !historyQuery.data?.items.length && (
            <div className="px-4 py-10 text-center text-sm text-muted-foreground">
              No detections matched the active filters.
            </div>
          )}
        </div>

        <div className="mt-4 flex flex-col gap-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <div>
            {historyQuery.data
              ? `Showing page ${historyQuery.data.pagination.page} of ${totalPages}`
              : "No history loaded"}
          </div>
          <div className="flex gap-2">
            <Button
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              size="sm"
              type="button"
              variant="outline"
            >
              Previous
            </Button>
            <Button
              disabled={page >= totalPages}
              onClick={() =>
                setPage((current) => Math.min(totalPages, current + 1))
              }
              size="sm"
              type="button"
              variant="outline"
            >
              Next
            </Button>
          </div>
        </div>
      </section>
    </Layout>
  );
}
