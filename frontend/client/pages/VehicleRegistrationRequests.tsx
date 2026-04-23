import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw, Send } from "lucide-react";

import Layout from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import {
  readApiError,
  VehicleRegistrationRequestListResponse,
} from "@/lib/api";

const initialFormState = {
  plate_number: "",
  owner_name: "",
  note: "",
};

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "--";
  }
  return new Date(value).toLocaleString();
}

export default function VehicleRegistrationRequests() {
  const queryClient = useQueryClient();
  const { authFetch, user } = useAuth();
  const [formState, setFormState] = useState(initialFormState);

  const requestsQuery = useQuery({
    queryKey: ["vehicle-registration-requests"],
    queryFn: async () => {
      const response = await authFetch("/vehicle-registration-requests");
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return (await response.json()) as VehicleRegistrationRequestListResponse;
    },
  });

  const createRequestMutation = useMutation({
    mutationFn: async () => {
      const response = await authFetch("/vehicle-registration-requests", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          plate_number: formState.plate_number,
          owner_name: formState.owner_name,
          note: formState.note || null,
        }),
      });
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Request submitted",
        description: "Your plate registration request has been sent to admin.",
      });
      setFormState(initialFormState);
      queryClient.invalidateQueries({
        queryKey: ["vehicle-registration-requests"],
      });
    },
    onError: (error) => {
      toast({
        title: "Request failed",
        description:
          error instanceof Error
            ? error.message
            : "Unable to submit the registration request.",
        variant: "destructive",
      });
    },
  });

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await createRequestMutation.mutateAsync();
  };

  return (
    <Layout
      subtitle="Send a registration request to admin instead of writing directly to the vehicle registry."
      title="Plate Registration Requests"
      actions={
        <Button
          onClick={() => {
            queryClient.invalidateQueries({
              queryKey: ["vehicle-registration-requests"],
            });
          }}
          size="sm"
          type="button"
          variant="outline"
        >
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </Button>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
        <section className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold tracking-tight">
                Submit request
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Admin will review the request before the plate is added to the
                registry.
              </p>
            </div>
            <StatusBadge value={user?.role ?? "OPERATOR"} />
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Plate number
              </label>
              <Input
                className="font-mono uppercase"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    plate_number: event.target.value.toUpperCase(),
                  }))
                }
                placeholder="51F-123.45"
                required
                value={formState.plate_number}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Owner name
              </label>
              <Input
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    owner_name: event.target.value,
                  }))
                }
                placeholder="Vehicle owner or resident name"
                required
                value={formState.owner_name}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Note for admin
              </label>
              <Textarea
                className="min-h-24"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    note: event.target.value,
                  }))
                }
                placeholder="Reason for registration, apartment number, or supporting context"
                value={formState.note}
              />
            </div>

            <Button
              className="w-full"
              disabled={createRequestMutation.isPending}
              type="submit"
            >
              <Send className="h-4 w-4" />
              Send request
            </Button>
          </form>
        </section>

        <section className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-foreground">
              My requests
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              You can track whether each request is pending, approved, or
              rejected.
            </p>
          </div>

          <div className="mt-5 overflow-hidden rounded-2xl border border-border">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px]">
                <thead className="bg-background/80">
                  <tr className="text-left text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    <th className="px-4 py-3 font-medium">Plate</th>
                    <th className="px-4 py-3 font-medium">Owner</th>
                    <th className="px-4 py-3 font-medium">Note</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Requested</th>
                    <th className="px-4 py-3 font-medium">Reviewed</th>
                  </tr>
                </thead>
                <tbody>
                  {requestsQuery.data?.items.map((request) => (
                    <tr
                      className="border-t border-border/80 text-sm text-foreground"
                      key={request.id}
                    >
                      <td className="px-4 py-4 font-mono text-base">
                        {request.plate_number}
                      </td>
                      <td className="px-4 py-4">{request.owner_name}</td>
                      <td className="px-4 py-4 text-muted-foreground">
                        {request.note || "--"}
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge value={request.status} />
                      </td>
                      <td className="px-4 py-4 text-muted-foreground">
                        {formatTimestamp(request.created_at)}
                      </td>
                      <td className="px-4 py-4 text-muted-foreground">
                        {request.reviewed_at
                          ? `${formatTimestamp(request.reviewed_at)}${request.reviewed_by_email ? ` by ${request.reviewed_by_email}` : ""}`
                          : "--"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {!requestsQuery.isLoading && !requestsQuery.data?.items.length && (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                No registration requests submitted yet.
              </div>
            )}

            {requestsQuery.isLoading && (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                Loading your requests...
              </div>
            )}
          </div>
        </section>
      </div>
    </Layout>
  );
}
