import VehicleRegistrationRequests from "./VehicleRegistrationRequests";
import VehicleRegistryAdmin from "./VehicleRegistryAdmin";

import { useAuth } from "@/lib/auth";

export default function Vehicles() {
  const { user } = useAuth();

  if (user?.role === "ADMIN") {
    return <VehicleRegistryAdmin />;
  }

  return <VehicleRegistrationRequests />;
}
