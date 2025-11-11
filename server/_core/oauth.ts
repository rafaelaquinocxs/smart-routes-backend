import type { Express, Request, Response } from "express";

/**
 * OAuth routes are disabled - using JWT authentication instead
 * This file is kept for compatibility but all OAuth functionality has been removed
 */
export function registerOAuthRoutes(app: Express) {
  // OAuth callback is disabled - all authentication uses JWT
  app.get("/api/oauth/callback", (req: Request, res: Response) => {
    res.status(410).json({
      error: "OAuth is disabled",
      message: "This application uses JWT authentication instead of OAuth",
    });
  });

  // Catch-all for any other OAuth-related routes
  app.get("/api/oauth/*", (req: Request, res: Response) => {
    res.status(410).json({
      error: "OAuth is disabled",
      message: "This application uses JWT authentication instead of OAuth",
    });
  });
}
