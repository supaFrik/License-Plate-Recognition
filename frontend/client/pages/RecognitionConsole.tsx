import {
  ChangeEvent,
  startTransition,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Camera,
  Clock3,
  Film,
  Image as ImageIcon,
  RefreshCcw,
  ShieldAlert,
  Upload,
} from "lucide-react";

import Layout from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { usePageVisibility } from "@/hooks/use-page-visibility";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import {
  CameraListResponse,
  Detection,
  DetectionLiveResponse,
  DetectionRecognizeResponse,
  readApiError,
} from "@/lib/api";

function formatDateTime(timestamp: string) {
  return new Date(timestamp).toLocaleString();
}

function describeVehicleStatus(detection: Detection) {
  switch (detection.visitor_type) {
    case "BANNED":
      return {
        title: "Banned vehicle detected",
        description: `${detection.plate_number} has been flagged as banned at ${detection.camera_name}.`,
        variant: "destructive" as const,
      };
    case "CITIZEN":
      return {
        title: "Authorized vehicle detected",
        description: `${detection.plate_number} is a registered citizen vehicle at ${detection.camera_name}.`,
        variant: "default" as const,
      };
    default:
      return {
        title: "Guest vehicle detected",
        description: `${detection.plate_number} is currently unregistered and treated as a guest vehicle.`,
        variant: "default" as const,
      };
  }
}

function mergeDetections(nextItems: Detection[], currentItems: Detection[]) {
  const seen = new Set<number>();
  const merged = [...nextItems, ...currentItems].filter((item) => {
    if (seen.has(item.id)) {
      return false;
    }
    seen.add(item.id);
    return true;
  });

  return merged.sort((a, b) => b.id - a.id).slice(0, 12);
}

function isVideoFile(file: File | null) {
  return Boolean(file?.type?.startsWith("video/"));
}

function MediaPreview({
  previewUrl,
  file,
  className,
}: {
  previewUrl: string | null;
  file: File | null;
  className?: string;
}) {
  if (!previewUrl) {
    return (
      <div
        className={`flex items-center justify-center bg-background/80 px-6 text-center text-sm text-muted-foreground ${className ?? ""}`}
      >
        No uploaded media preview is currently available.
      </div>
    );
  }

  if (isVideoFile(file)) {
    return (
      <video
        className={className}
        controls
        loop
        muted
        playsInline
        src={previewUrl}
      />
    );
  }

  return (
    <img
      alt={file?.name ?? "Uploaded media preview"}
      className={className}
      src={previewUrl}
    />
  );
}

export default function RecognitionConsole() {
  const queryClient = useQueryClient();
  const { authFetch } = useAuth();
  const isVisible = usePageVisibility();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [lastResult, setLastResult] = useState<DetectionRecognizeResponse | null>(
    null,
  );
  const [liveDetections, setLiveDetections] = useState<Detection[]>([]);
  const [pollingError, setPollingError] = useState<string | null>(null);
  const latestIdRef = useRef(0);
  const hasLoadedInitialFeedRef = useRef(false);

  const camerasQuery = useQuery({
    queryKey: ["cameras"],
    queryFn: async () => {
      const response = await authFetch("/cameras");
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return (await response.json()) as CameraListResponse;
    },
  });

  const recognizeMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) {
        throw new Error("Choose an image or video before running recognition.");
      }

      const formData = new FormData();
      formData.append("file", selectedFile);
      if (selectedCameraId) {
        formData.append("camera_id", selectedCameraId);
      }

      const response = await authFetch("/detections/recognize", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return (await response.json()) as DetectionRecognizeResponse;
    },
    onSuccess: (payload) => {
      setLastResult(payload);
      if (payload.detection) {
        latestIdRef.current = Math.max(latestIdRef.current, payload.detection.id);
        startTransition(() => {
          setLiveDetections((current) =>
            mergeDetections([payload.detection as Detection], current),
          );
        });
        toast(describeVehicleStatus(payload.detection as Detection));
      } else {
        toast({
          title:
            payload.input_kind === "video"
              ? "No plate validated from video"
              : "No plate detected",
          description:
            payload.validation_note ??
            "The uploaded media did not produce a plate match.",
        });
      }
      queryClient.invalidateQueries({ queryKey: ["history"] });
    },
    onError: (error) => {
      toast({
        title: "Recognition failed",
        description:
          error instanceof Error
            ? error.message
            : "The uploaded media could not be processed.",
        variant: "destructive",
      });
    },
  });

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  useEffect(() => {
    if (!isVisible) {
      return;
    }

    let isActive = true;
    let timeoutId: number | undefined;

    const poll = async () => {
      try {
        const limit = latestIdRef.current === 0 ? 10 : 6;
        const response = await authFetch(
          `/detections/live?after_id=${latestIdRef.current}&limit=${limit}`,
        );
        if (!response.ok) {
          throw new Error(await readApiError(response));
        }

        const payload = (await response.json()) as DetectionLiveResponse;
        if (!isActive) {
          return;
        }

        latestIdRef.current = Math.max(latestIdRef.current, payload.latest_id);
        if (payload.items.length) {
          setPollingError(null);
          if (hasLoadedInitialFeedRef.current) {
            payload.items.forEach((detection) => {
              toast(describeVehicleStatus(detection));
            });
          }
          startTransition(() => {
            setLiveDetections((current) =>
              mergeDetections([...payload.items].reverse(), current),
            );
          });
        }
        hasLoadedInitialFeedRef.current = true;
      } catch (error) {
        if (isActive) {
          setPollingError(
            error instanceof Error
              ? error.message
              : "Live detections are temporarily unavailable.",
          );
        }
      } finally {
        if (isActive && isVisible) {
          timeoutId = window.setTimeout(poll, 2000);
        }
      }
    };

    poll();

    return () => {
      isActive = false;
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [authFetch, isVisible]);

  const activeDetection = useMemo(() => {
    return lastResult?.detection ?? liveDetections[0] ?? null;
  }, [lastResult?.detection, liveDetections]);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(nextFile ? URL.createObjectURL(nextFile) : null);
    setSelectedFile(nextFile);
    setLastResult(null);
  };

  const handleReset = () => {
    latestIdRef.current = 0;
    hasLoadedInitialFeedRef.current = false;
    setLiveDetections([]);
    setLastResult(null);
    setPollingError(null);
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(null);
  };

  const latestResultTitle =
    lastResult?.input_kind === "video"
      ? "Best validated video frame"
      : "Latest uploaded frame";

  return (
    <Layout
      subtitle="Live operator console optimized for fast intake, low-noise alerts, and high-confidence plate review."
      title="Detection Console"
      actions={
        <Button onClick={handleReset} size="sm" type="button" variant="outline">
          <RefreshCcw className="h-4 w-4" />
          Reset feed
        </Button>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_380px]">
        <div className="space-y-6">
          <section className="grid gap-4 md:grid-cols-3">
            <article className="rounded-2xl border border-border bg-card p-5">
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Activity className="h-4 w-4 text-primary" />
                Current ingest latency
              </div>
              <div className="mt-4 text-3xl font-semibold tracking-tight text-foreground">
                {lastResult ? `${lastResult.processing_ms.toFixed(0)} ms` : "--"}
              </div>
            </article>

            <article className="rounded-2xl border border-border bg-card p-5">
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <ShieldAlert className="h-4 w-4 text-primary" />
                Latest classification
              </div>
              <div className="mt-4">
                {activeDetection ? (
                  <StatusBadge value={activeDetection.visitor_type} />
                ) : (
                  <span className="text-sm text-muted-foreground">
                    Awaiting detections
                  </span>
                )}
              </div>
            </article>

            <article className="rounded-2xl border border-border bg-card p-5">
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Clock3 className="h-4 w-4 text-primary" />
                Feed state
              </div>
              <div className="mt-4 text-sm text-foreground">
                {isVisible ? "Live polling active" : "Polling paused"}
              </div>
            </article>
          </section>

          <section className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-foreground">
                  Recognition intake
                </h2>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
                  Submit a still image or a short video. Video uploads are sampled
                  into a bounded set of frames, then the console keeps the plate
                  with the strongest repeated confidence.
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_280px]">
              <div className="rounded-2xl border border-dashed border-border bg-background/70 p-5">
                <label className="block cursor-pointer overflow-hidden rounded-2xl border border-border bg-card/70 transition hover:border-primary/30 hover:bg-primary/5">
                  <div className="relative aspect-[4/3] overflow-hidden">
                    {previewUrl ? (
                      <MediaPreview
                        className="h-full w-full object-cover"
                        file={selectedFile}
                        previewUrl={previewUrl}
                      />
                    ) : (
                      <div className="flex h-full flex-col items-center justify-center px-6 text-center">
                        <Upload className="h-10 w-10 text-primary" />
                        <div className="mt-4 text-base font-medium text-foreground">
                          Upload detection media
                        </div>
                        <div className="mt-2 text-sm text-muted-foreground">
                          JPG, PNG, WEBP, or MP4. Short clips are sampled for the
                          best validated frame.
                        </div>
                      </div>
                    )}
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/95 via-slate-950/55 to-transparent px-5 pb-5 pt-10">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-slate-950/80 text-primary">
                          {isVideoFile(selectedFile) ? (
                            <Film className="h-5 w-5" />
                          ) : (
                            <ImageIcon className="h-5 w-5" />
                          )}
                        </div>
                        <div>
                          <div className="text-sm font-medium text-white">
                            {selectedFile ? selectedFile.name : "Select media"}
                          </div>
                          <div className="text-xs uppercase tracking-[0.22em] text-slate-300">
                            Preview updates on every upload
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <input
                    accept="image/*,video/*"
                    className="hidden"
                    onChange={handleFileChange}
                    type="file"
                  />
                </label>
              </div>

              <div className="space-y-4 rounded-2xl border border-border bg-background/60 p-5">
                <div className="space-y-2">
                  <label className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    Camera
                  </label>
                  <select
                    className="flex h-10 w-full rounded-md border border-border bg-card px-3 text-sm text-foreground"
                    onChange={(event) => setSelectedCameraId(event.target.value)}
                    value={selectedCameraId}
                  >
                    <option value="">Auto-route to upload console</option>
                    {camerasQuery.data?.items.map((camera) => (
                      <option key={camera.id} value={camera.id}>
                        {camera.location_name}
                      </option>
                    ))}
                  </select>
                </div>

                <Button
                  className="w-full"
                  disabled={!selectedFile || recognizeMutation.isPending}
                  onClick={() => recognizeMutation.mutate()}
                  type="button"
                >
                  {recognizeMutation.isPending
                    ? isVideoFile(selectedFile)
                      ? "Validating video frames..."
                      : "Analyzing frame..."
                    : isVideoFile(selectedFile)
                      ? "Run video recognition"
                      : "Run recognition"}
                </Button>

                <div className="rounded-2xl border border-border bg-card/70 p-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2 text-foreground">
                    <Camera className="h-4 w-4 text-primary" />
                    Performance note
                  </div>
                  <p className="mt-2 leading-6">
                    Images still use the fastest path. Videos are sampled into a
                    capped frame set so we can validate repeated plates without
                    brute-forcing the full clip.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold tracking-tight text-foreground">
                  Latest result
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Most recent recognized media with plate classification context.
                </p>
              </div>
              {activeDetection ? (
                <StatusBadge value={activeDetection.visitor_type} />
              ) : null}
            </div>

            {lastResult ? (
              <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
                <div className="overflow-hidden rounded-2xl border border-border bg-background/60">
                  <MediaPreview
                    className="aspect-[16/10] w-full object-cover"
                    file={selectedFile}
                    previewUrl={previewUrl}
                  />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-border bg-background/60 p-4 md:col-span-2">
                    <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      Source
                    </div>
                    <div className="mt-3 flex items-center gap-3 text-lg font-semibold text-foreground">
                      {lastResult.input_kind === "video" ? (
                        <Film className="h-5 w-5 text-primary" />
                      ) : (
                        <ImageIcon className="h-5 w-5 text-primary" />
                      )}
                      {latestResultTitle}
                    </div>
                    <p className="mt-3 text-sm leading-6 text-muted-foreground">
                      {lastResult.validation_note ??
                        "Latest recognition metadata will appear here."}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-border bg-background/60 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      Plate
                    </div>
                    <div className="mt-3 font-mono text-2xl font-semibold text-foreground">
                      {lastResult.plate_number ?? "--"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border bg-background/60 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      Confidence
                    </div>
                    <div className="mt-3 text-2xl font-semibold text-foreground">
                      {lastResult.confidence
                        ? `${(lastResult.confidence * 100).toFixed(2)}%`
                        : "--"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border bg-background/60 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      Sampled frames
                    </div>
                    <div className="mt-3 text-lg font-semibold text-foreground">
                      {lastResult.sampled_frames}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border bg-background/60 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      Selected frame
                    </div>
                    <div className="mt-3 text-lg font-semibold text-foreground">
                      {lastResult.selected_frame_index ?? "--"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border bg-background/60 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      Camera
                    </div>
                    <div className="mt-3 text-lg font-semibold text-foreground">
                      {lastResult.detection?.camera_name ?? "Upload console"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border bg-background/60 p-4">
                    <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      Detected at
                    </div>
                    <div className="mt-3 text-lg font-semibold text-foreground">
                      {lastResult.detection
                        ? formatDateTime(lastResult.detection.timestamp)
                        : "--"}
                    </div>
                  </div>
                </div>
              </div>
            ) : activeDetection ? (
              <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    Plate
                  </div>
                  <div className="mt-3 font-mono text-2xl font-semibold text-foreground">
                    {activeDetection.plate_number}
                  </div>
                </div>
                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    Confidence
                  </div>
                  <div className="mt-3 text-2xl font-semibold text-foreground">
                    {(activeDetection.confidence * 100).toFixed(2)}%
                  </div>
                </div>
                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    Camera
                  </div>
                  <div className="mt-3 text-lg font-semibold text-foreground">
                    {activeDetection.camera_name}
                  </div>
                </div>
                <div className="rounded-2xl border border-border bg-background/60 p-4">
                  <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    Detected at
                  </div>
                  <div className="mt-3 text-lg font-semibold text-foreground">
                    {formatDateTime(activeDetection.timestamp)}
                  </div>
                </div>
              </div>
            ) : previewUrl ? (
              <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="overflow-hidden rounded-2xl border border-border bg-background/60">
                  <MediaPreview
                    className="aspect-[16/10] w-full object-cover"
                    file={selectedFile}
                    previewUrl={previewUrl}
                  />
                </div>
                <div className="rounded-2xl border border-border bg-background/60 p-5 text-sm text-muted-foreground">
                  <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    Pending upload
                  </div>
                  <div className="mt-3 font-medium text-foreground">
                    {selectedFile?.name ?? "Uploaded media"}
                  </div>
                  <p className="mt-3 leading-6">
                    The uploaded media remains visible after every upload so the
                    operator can verify the exact frame or clip being analyzed.
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-6 rounded-2xl border border-border bg-background/60 px-4 py-10 text-center text-sm text-muted-foreground">
                Upload a frame, upload a short video, or wait for live detections
                to begin populating the console.
              </div>
            )}
          </section>
        </div>

        <aside className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                Live detections
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Incremental feed, refreshed every 2 seconds while visible.
              </p>
            </div>
          </div>

          {pollingError ? (
            <div className="mt-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
              {pollingError}
            </div>
          ) : null}

          <div className="mt-5 space-y-3">
            {liveDetections.map((detection) => (
              <article
                className="rounded-2xl border border-border bg-background/60 p-4"
                key={detection.id}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="font-mono text-lg font-semibold text-foreground">
                      {detection.plate_number}
                    </div>
                    <div className="mt-1 text-xs uppercase tracking-[0.24em] text-muted-foreground">
                      {detection.camera_name}
                    </div>
                  </div>
                  <StatusBadge value={detection.visitor_type} />
                </div>
                <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                  <span>{(detection.confidence * 100).toFixed(2)}% confidence</span>
                  <span>{formatDateTime(detection.timestamp)}</span>
                </div>
              </article>
            ))}

            {!liveDetections.length && (
              <div className="rounded-2xl border border-border bg-background/60 px-4 py-10 text-center text-sm text-muted-foreground">
                No detections yet. The feed will populate as soon as new frames
                or validated video clips are recognized.
              </div>
            )}
          </div>
        </aside>
      </div>
    </Layout>
  );
}
