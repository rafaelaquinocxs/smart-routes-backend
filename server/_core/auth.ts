import { Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import type { User } from '../../drizzle/schema';
import * as db from '../db';
import { ENV } from './env';

export const JWT_COOKIE_NAME = 'smartoures-jwt';

export interface JWTPayload {
  userId: number;
  email: string;
  role: string;
}

/**
 * Extract and verify JWT token from request
 */
export async function authenticateRequest(req: Request): Promise<User | null> {
  try {
    // Get token from cookie
    const token = req.cookies?.[JWT_COOKIE_NAME];
    
    if (!token) {
      return null;
    }

    // Verify token
    const payload = jwt.verify(token, ENV.jwtSecret) as JWTPayload;
    
    // Get user from database
    const user = await db.getUserById(payload.userId);
    
    if (!user) {
      return null;
    }

    return user;
  } catch (error) {
    console.error('[Auth] Token verification failed:', error);
    return null;
  }
}

/**
 * Generate JWT token
 */
export function generateToken(payload: JWTPayload): string {
  return jwt.sign(payload, ENV.jwtSecret, {
    expiresIn: '7d',
  });
}

/**
 * Set JWT token in cookie
 */
export function setTokenCookie(res: Response, token: string): void {
  res.cookie(JWT_COOKIE_NAME, token, {
    httpOnly: true,
    secure: ENV.isProduction,
    sameSite: 'lax',
    maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
  });
}

/**
 * Clear JWT token from cookie
 */
export function clearTokenCookie(res: Response): void {
  res.clearCookie(JWT_COOKIE_NAME, {
    httpOnly: true,
    secure: ENV.isProduction,
    sameSite: 'lax',
  });
}
