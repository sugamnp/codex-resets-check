import { NextRequest, NextResponse } from "next/server";
import { getResetStatus } from "@/lib/status";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const configured = process.env.CRON_SECRET;
  const auth = request.headers.get("authorization");

  if (configured && auth !== `Bearer ${configured}`) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  return NextResponse.json(await getResetStatus());
}
