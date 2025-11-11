import { eq, desc, sql } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users, containers, sensorReadings, routeHistory, routeSavings, InsertRouteHistory, InsertRouteSavings } from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.email || !user.passwordHash) {
    throw new Error("User email and passwordHash are required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      email: user.email,
      passwordHash: user.passwordHash,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "companyName", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByEmail(email: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.email, email)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

export async function getUserById(id: number) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.id, id)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

export async function getContainers() {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get containers: database not available");
    return [];
  }

  return await db.select().from(containers);
}

export async function getLatestSensorReadings() {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get sensor readings: database not available");
    return [];
  }

  return await db.select().from(sensorReadings);
}


// Route history functions
export async function saveRoute(route: InsertRouteHistory) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot save route: database not available");
    return null;
  }

  try {
    const result = await db.insert(routeHistory).values(route);
    // Get the last inserted route
    const lastRoute = await db.select().from(routeHistory).orderBy(routeHistory.id).limit(1);
    const routeId = lastRoute[0]?.id;
    console.log("[Database] Saved route with ID:", routeId);
    return { insertId: routeId };
  } catch (error) {
    console.error("[Database] Failed to save route:", error);
    throw error;
  }
}

export async function saveRouteSavings(savings: InsertRouteSavings) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot save route savings: database not available");
    return null;
  }

  try {
    console.log("[Database] Saving route savings:", savings);
    const result = await db.insert(routeSavings).values(savings);
    console.log("[Database] Saved route savings, result:", result);
    return result;
  } catch (error) {
    console.error("[Database] Failed to save route savings:", error);
    throw error;
  }
}

export async function getRouteHistory(limit: number = 100) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get route history: database not available");
    return [];
  }

  try {
    return await db.select().from(routeHistory).orderBy(desc(routeHistory.routeDate)).limit(limit);
  } catch (error) {
    console.error("[Database] Failed to get route history:", error);
    return [];
  }
}

export async function getRouteSavingsByRouteId(routeId: number) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get route savings: database not available");
    return null;
  }

  try {
    const result = await db.select().from(routeSavings).where(eq(routeSavings.routeId, routeId)).limit(1);
    return result.length > 0 ? result[0] : null;
  } catch (error) {
    console.error("[Database] Failed to get route savings:", error);
    return null;
  }
}

export async function getTotalSavings() {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get total savings: database not available");
    return null;
  }

  try {
    const result = await db.select({
      totalFuel: sql<number>`SUM(${routeSavings.fuelSaved})`,
      totalCo2: sql<number>`SUM(${routeSavings.co2Saved})`,
      totalCost: sql<number>`SUM(${routeSavings.costSaved})`,
      totalTime: sql<number>`SUM(${routeSavings.timeSaved})`,
      routeCount: sql<number>`COUNT(*)`,
    }).from(routeSavings);

    return result.length > 0 ? result[0] : null;
  } catch (error) {
    console.error("[Database] Failed to get total savings:", error);
    return null;
  }
}

export async function getSavingsByPeriod(period: 'day' | 'month' | 'year') {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get savings by period: database not available");
    return [];
  }

  try {
    let dateFormat = '%Y-%m-%d'; // day
    if (period === 'month') dateFormat = '%Y-%m';
    if (period === 'year') dateFormat = '%Y';

    const result = await db.select({
      period: sql<string>`DATE_FORMAT(${routeHistory.routeDate}, '${sql.raw(dateFormat)}')`,
      totalFuel: sql<number>`SUM(${routeSavings.fuelSaved})`,
      totalCo2: sql<number>`SUM(${routeSavings.co2Saved})`,
      totalCost: sql<number>`SUM(${routeSavings.costSaved})`,
      totalTime: sql<number>`SUM(${routeSavings.timeSaved})`,
      routeCount: sql<number>`COUNT(${routeHistory.id})`,
    }).from(routeHistory)
      .leftJoin(routeSavings, eq(routeHistory.id, routeSavings.routeId))
      .groupBy(sql`DATE_FORMAT(${routeHistory.routeDate}, '${sql.raw(dateFormat)}')`);

    return result;
  } catch (error) {
    console.error("[Database] Failed to get savings by period:", error);
    return [];
  }
}
