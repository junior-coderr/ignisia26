import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const BACKEND_ORIGIN = process.env.BACKEND_API_ORIGIN || "http://127.0.0.1:8000";

function buildBackendUrl(pathSegments: string[], request: NextRequest) {
  const incomingUrl = new URL(request.url);
  const backendUrl = new URL(`/api/${pathSegments.join("/")}`, BACKEND_ORIGIN);
  backendUrl.search = incomingUrl.search;
  return backendUrl;
}

function buildForwardHeaders(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");
  return headers;
}

function buildResponseHeaders(headers: Headers) {
  const nextHeaders = new Headers(headers);
  nextHeaders.delete("content-length");
  nextHeaders.delete("transfer-encoding");
  return nextHeaders;
}

async function proxy(request: NextRequest, pathSegments: string[]) {
  const init: RequestInit = {
    method: request.method,
    headers: buildForwardHeaders(request),
    redirect: "manual",
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = request.body;
    (init as any).duplex = "half";
  }

  try {
    const response = await fetch(buildBackendUrl(pathSegments, request), init);
    return new Response(response.body, {
      status: response.status,
      headers: buildResponseHeaders(response.headers),
    });
  } catch {
    return Response.json(
      {
        detail: "Backend service unavailable. Start the FastAPI server on http://127.0.0.1:8000 and retry.",
        code: "backend_unavailable",
      },
      { status: 503 },
    );
  }
}

type RouteContext = {
  params: {
    path?: string[];
  };
};

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context.params.path || []);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context.params.path || []);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context.params.path || []);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context.params.path || []);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context.params.path || []);
}

export async function OPTIONS(request: NextRequest, context: RouteContext) {
  return proxy(request, context.params.path || []);
}
