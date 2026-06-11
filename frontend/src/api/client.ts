import type {
  BeamRequest,
  BeamResponse,
  BearingOptimizeRequest,
  BearingOptimizeResponse,
  BearingRequest,
  BearingResponse,
  GearOptimizeRequest,
  GearOptimizeResponse,
  GearRequest,
  GearResponse,
  KeyOptimizeRequest,
  KeyOptimizeResponse,
  KeyRequest,
  KeyResponse,
  OptimizeRequest,
  OptimizeResponse,
  ShaftOptimizeRequest,
  ShaftOptimizeResponse,
  ShaftRequest,
  ShaftResponse,
} from "../types";

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function flattenDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e: any) => {
        const loc = Array.isArray(e?.loc) ? e.loc.join(".") : "";
        const msg = e?.msg ?? JSON.stringify(e);
        return loc ? `${loc} — ${msg}` : msg;
      })
      .join(" | ");
  }
  return JSON.stringify(detail);
}

export async function calculateBeam(req: BeamRequest): Promise<BeamResponse> {
  const r = await fetch(`${API_BASE}/calculate/beam`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!r.ok) {
    let message = `HTTP ${r.status}`;
    try {
      const body = await r.json();
      if (body?.detail !== undefined) message = flattenDetail(body.detail);
    } catch {
      // body wasn't JSON
    }
    throw new ApiError(r.status, message);
  }

  return (await r.json()) as BeamResponse;
}

export async function optimizeBeam(
  req: OptimizeRequest,
): Promise<OptimizeResponse> {
  return postJson<OptimizeResponse>("/optimize/beam", req);
}

export async function calculateShaft(req: ShaftRequest): Promise<ShaftResponse> {
  return postJson<ShaftResponse>("/calculate/shaft", req);
}

export async function optimizeShaft(
  req: ShaftOptimizeRequest,
): Promise<ShaftOptimizeResponse> {
  return postJson<ShaftOptimizeResponse>("/optimize/shaft", req);
}

export async function calculateKey(req: KeyRequest): Promise<KeyResponse> {
  return postJson<KeyResponse>("/calculate/key", req);
}

export async function optimizeKey(
  req: KeyOptimizeRequest,
): Promise<KeyOptimizeResponse> {
  return postJson<KeyOptimizeResponse>("/optimize/key", req);
}

export async function calculateBearing(
  req: BearingRequest,
): Promise<BearingResponse> {
  return postJson<BearingResponse>("/calculate/bearing", req);
}

export async function optimizeBearing(
  req: BearingOptimizeRequest,
): Promise<BearingOptimizeResponse> {
  return postJson<BearingOptimizeResponse>("/optimize/bearing", req);
}

export async function calculateGear(req: GearRequest): Promise<GearResponse> {
  return postJson<GearResponse>("/calculate/gear", req);
}

export async function optimizeGear(
  req: GearOptimizeRequest,
): Promise<GearOptimizeResponse> {
  return postJson<GearOptimizeResponse>("/optimize/gear", req);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let message = `HTTP ${r.status}`;
    try {
      const j = await r.json();
      if (j?.detail !== undefined) message = flattenDetail(j.detail);
    } catch {
      /* body wasn't JSON */
    }
    throw new ApiError(r.status, message);
  }
  return (await r.json()) as T;
}
