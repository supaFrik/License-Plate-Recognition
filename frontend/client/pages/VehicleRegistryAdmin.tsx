import {
  FormEvent,
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, PencilLine, RefreshCcw, Trash2, X } from "lucide-react";

import Layout from "@/components/Layout";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import {
  readApiError,
  Vehicle,
  VehicleListResponse,
  VehicleRegistrationRequestListResponse,
  VehicleStatus,
} from "@/lib/api";

const PAGE_SIZE = 12;

const initialFormState = {
  plate_number: "",
  owner_name: "",
  status: "CITIZEN" as VehicleStatus,
};

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return "--";
  }
  return new Date(value).toLocaleString();
}

export default function VehicleRegistryAdmin() {
  const queryClient = useQueryClient();
  const { authFetch, user } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<VehicleStatus | "ALL">(
    "ALL",
  );
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null);
  const [formState, setFormState] = useState(initialFormState);
  const deferredSearch = useDeferredValue(search);
  const debouncedSearch = useDebouncedValue(deferredSearch, 300);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statusFilter]);

  const vehicleQuery = useQuery({
    queryKey: ["vehicles", page, debouncedSearch, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: `${page}`,
        page_size: `${PAGE_SIZE}`,
      });
      if (debouncedSearch) {
        params.set("query", debouncedSearch);
      }
      if (statusFilter !== "ALL") {
        params.set("status", statusFilter);
      }

      const response = await authFetch(`/vehicles?${params.toString()}`);
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return (await response.json()) as VehicleListResponse;
    },
  });

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

  const saveVehicleMutation = useMutation({
    mutationFn: async () => {
      const isEditing = Boolean(editingVehicle);
      const response = await authFetch(
        isEditing ? `/vehicles/${editingVehicle?.id}` : "/vehicles",
        {
          method: isEditing ? "PATCH" : "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formState),
        },
      );
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: editingVehicle ? "Vehicle updated" : "Vehicle registered",
        description: "The registry has been synchronized successfully.",
      });
      setEditingVehicle(null);
      setFormState(initialFormState);
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
    onError: (error) => {
      toast({
        title: "Registry update failed",
        description:
          error instanceof Error
            ? error.message
            : "Unable to update the vehicle registry.",
        variant: "destructive",
      });
    },
  });

  const deleteVehicleMutation = useMutation({
    mutationFn: async (vehicleId: number) => {
      const response = await authFetch(`/vehicles/${vehicleId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
    },
    onSuccess: () => {
      toast({
        title: "Vehicle removed",
        description: "The vehicle was removed from the registry.",
      });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
    onError: (error) => {
      toast({
        title: "Delete failed",
        description:
          error instanceof Error
            ? error.message
            : "Unable to remove the vehicle.",
        variant: "destructive",
      });
    },
  });

  const approveRequestMutation = useMutation({
    mutationFn: async (requestId: number) => {
      const response = await authFetch(
        `/vehicle-registration-requests/${requestId}/approve`,
        {
          method: "POST",
        },
      );
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Request approved",
        description: "The plate has been added to the vehicle registry.",
      });
      queryClient.invalidateQueries({
        queryKey: ["vehicle-registration-requests"],
      });
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
    },
    onError: (error) => {
      toast({
        title: "Approval failed",
        description:
          error instanceof Error
            ? error.message
            : "Unable to approve the registration request.",
        variant: "destructive",
      });
    },
  });

  const rejectRequestMutation = useMutation({
    mutationFn: async (requestId: number) => {
      const response = await authFetch(
        `/vehicle-registration-requests/${requestId}/reject`,
        {
          method: "POST",
        },
      );
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Request rejected",
        description: "The registration request has been rejected.",
      });
      queryClient.invalidateQueries({
        queryKey: ["vehicle-registration-requests"],
      });
    },
    onError: (error) => {
      toast({
        title: "Rejection failed",
        description:
          error instanceof Error
            ? error.message
            : "Unable to reject the registration request.",
        variant: "destructive",
      });
    },
  });

  const totalPages = useMemo(() => {
    const total = vehicleQuery.data?.pagination.total ?? 0;
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }, [vehicleQuery.data?.pagination.total]);

  const pendingRequests =
    requestsQuery.data?.items.filter(
      (request) => request.status === "PENDING",
    ) ?? [];

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await saveVehicleMutation.mutateAsync();
  };

  return (
    <Layout
      subtitle="Maintain registered vehicles and approve operator-submitted plate requests."
      title="Vehicle Registry"
      actions={
        <Button
          onClick={() => {
            queryClient.invalidateQueries({ queryKey: ["vehicles"] });
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
      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <section className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold tracking-tight">
                {editingVehicle ? "Edit vehicle" : "Register vehicle"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Maintain resident and banned vehicle records.
              </p>
            </div>
            <StatusBadge value={user?.role ?? "ADMIN"} />
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
                placeholder="Resident or account owner"
                required
                value={formState.owner_name}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Access status
              </label>
              <select
                className="flex h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground"
                onChange={(event) =>
                  setFormState((current) => ({
                    ...current,
                    status: event.target.value as VehicleStatus,
                  }))
                }
                value={formState.status}
              >
                <option value="CITIZEN">CITIZEN</option>
                <option value="BANNED">BANNED</option>
              </select>
            </div>

            <div className="flex gap-3">
              <Button
                className="flex-1"
                disabled={saveVehicleMutation.isPending}
                type="submit"
              >
                {editingVehicle ? (
                  <>
                    <PencilLine className="h-4 w-4" />
                    Save changes
                  </>
                ) : (
                  "Add vehicle"
                )}
              </Button>
              {editingVehicle && (
                <Button
                  onClick={() => {
                    setEditingVehicle(null);
                    setFormState(initialFormState);
                  }}
                  type="button"
                  variant="outline"
                >
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </section>

        <section className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                Registration requests
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Review operator requests before plates are added to the
                registry.
              </p>
            </div>
            <div className="text-sm text-muted-foreground">
              {pendingRequests.length} pending
            </div>
          </div>

          <div className="mt-5 overflow-hidden rounded-2xl border border-border">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px]">
                <thead className="bg-background/80">
                  <tr className="text-left text-xs uppercase tracking-[0.24em] text-muted-foreground">
                    <th className="px-4 py-3 font-medium">Plate</th>
                    <th className="px-4 py-3 font-medium">Owner</th>
                    <th className="px-4 py-3 font-medium">Requester</th>
                    <th className="px-4 py-3 font-medium">Note</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Requested</th>
                    <th className="px-4 py-3 font-medium">Actions</th>
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
                        {request.requester_email}
                      </td>
                      <td className="px-4 py-4 text-muted-foreground">
                        {request.note || "--"}
                      </td>
                      <td className="px-4 py-4">
                        <StatusBadge value={request.status} />
                      </td>
                      <td className="px-4 py-4 text-muted-foreground">
                        {formatTimestamp(request.created_at)}
                      </td>
                      <td className="px-4 py-4">
                        {request.status === "PENDING" ? (
                          <div className="flex gap-2">
                            <Button
                              disabled={approveRequestMutation.isPending}
                              onClick={() =>
                                approveRequestMutation.mutate(request.id)
                              }
                              size="sm"
                              type="button"
                              variant="outline"
                            >
                              <Check className="h-4 w-4" />
                              Approve
                            </Button>
                            <Button
                              disabled={rejectRequestMutation.isPending}
                              onClick={() =>
                                rejectRequestMutation.mutate(request.id)
                              }
                              size="sm"
                              type="button"
                              variant="outline"
                            >
                              <X className="h-4 w-4" />
                              Reject
                            </Button>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">
                            {request.reviewed_at
                              ? `${formatTimestamp(request.reviewed_at)}${request.reviewed_by_email ? ` by ${request.reviewed_by_email}` : ""}`
                              : "Reviewed"}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {!requestsQuery.isLoading && !requestsQuery.data?.items.length && (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                No registration requests available.
              </div>
            )}

            {requestsQuery.isLoading && (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                Loading registration requests...
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="mt-6 rounded-2xl border border-border bg-card p-5 shadow-lg shadow-black/10">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-foreground">
              Active records
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Registry changes affect future visitor classification immediately.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-[1fr_180px]">
            <Input
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by plate or owner"
              value={search}
            />
            <select
              className="flex h-10 rounded-md border border-border bg-background px-3 text-sm text-foreground"
              onChange={(event) =>
                setStatusFilter(event.target.value as VehicleStatus | "ALL")
              }
              value={statusFilter}
            >
              <option value="ALL">All statuses</option>
              <option value="CITIZEN">CITIZEN</option>
              <option value="BANNED">BANNED</option>
            </select>
          </div>
        </div>

        <div className="mt-5 overflow-hidden rounded-2xl border border-border">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px]">
              <thead className="bg-background/80">
                <tr className="text-left text-xs uppercase tracking-[0.24em] text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Plate</th>
                  <th className="px-4 py-3 font-medium">Owner</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {vehicleQuery.data?.items.map((vehicle) => (
                  <tr
                    className="border-t border-border/80 text-sm text-foreground"
                    key={vehicle.id}
                  >
                    <td className="px-4 py-4 font-mono text-base">
                      {vehicle.plate_number}
                    </td>
                    <td className="px-4 py-4">{vehicle.owner_name}</td>
                    <td className="px-4 py-4">
                      <StatusBadge value={vehicle.status} />
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex gap-2">
                        <Button
                          onClick={() => {
                            setEditingVehicle(vehicle);
                            setFormState({
                              plate_number: vehicle.plate_number,
                              owner_name: vehicle.owner_name,
                              status: vehicle.status,
                            });
                          }}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          <PencilLine className="h-4 w-4" />
                          Edit
                        </Button>
                        <Button
                          disabled={deleteVehicleMutation.isPending}
                          onClick={() =>
                            deleteVehicleMutation.mutate(vehicle.id)
                          }
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          <Trash2 className="h-4 w-4" />
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!vehicleQuery.isLoading && !vehicleQuery.data?.items.length && (
            <div className="px-4 py-10 text-center text-sm text-muted-foreground">
              No vehicle records matched the current filters.
            </div>
          )}

          {vehicleQuery.isLoading && (
            <div className="px-4 py-10 text-center text-sm text-muted-foreground">
              Loading vehicle records...
            </div>
          )}
        </div>

        <div className="mt-4 flex flex-col gap-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <div>
            {vehicleQuery.data
              ? `Showing page ${vehicleQuery.data.pagination.page} of ${totalPages}`
              : "No data loaded"}
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
