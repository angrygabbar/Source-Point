import { NextResponse, type NextRequest } from "next/server";

const MODULE_PREFIX = "/coinback";

// SourcePoint owns sign-in. The old CoinBack login URL now returns to the module.
export function middleware(req: NextRequest) {
  const pathname = req.nextUrl.pathname;
  if (pathname === "/login" || pathname === `${MODULE_PREFIX}/login`) {
    return NextResponse.redirect(new URL(`${MODULE_PREFIX}/`, req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!coinback-api|_next/static|_next/image|favicon.svg|robots.txt).*)"],
};
