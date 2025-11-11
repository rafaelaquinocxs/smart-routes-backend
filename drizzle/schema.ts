import { int, mysqlEnum, mysqlTable, text, timestamp, varchar, decimal, float } from "drizzle-orm/mysql-core";

/**
 * Core user table with JWT authentication support.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).unique(), // Optional for OAuth
  email: varchar("email", { length: 320 }).unique(),
  passwordHash: varchar("passwordHash", { length: 255 }), // For JWT auth
  name: text("name"),
  companyName: text("companyName"), // For waste collection companies
  loginMethod: varchar("loginMethod", { length: 64 }).default("jwt"),
  role: mysqlEnum("role", ["user", "admin", "company"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * Containers table - represents trash containers with sensors
 */
export const containers = mysqlTable("containers", {
  id: int("id").autoincrement().primaryKey(),
  sensorId: varchar("sensorId", { length: 64 }).notNull().unique(), // Unique sensor identifier
  name: varchar("name", { length: 255 }).notNull(), // e.g., "Container 01"
  latitude: decimal("latitude", { precision: 10, scale: 8 }).notNull(),
  longitude: decimal("longitude", { precision: 11, scale: 8 }).notNull(),
  capacity: int("capacity").default(100), // Capacity in liters or percentage
  status: mysqlEnum("status", ["active", "inactive", "maintenance"]).default("active"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Container = typeof containers.$inferSelect;
export type InsertContainer = typeof containers.$inferInsert;

/**
 * Sensor readings table - stores historical sensor data
 */
export const sensorReadings = mysqlTable("sensorReadings", {
  id: int("id").autoincrement().primaryKey(),
  containerId: int("containerId").notNull(), // Foreign key to containers
  sensorId: varchar("sensorId", { length: 64 }).notNull(),
  level: int("level").notNull(), // Fill level in percentage (0-100)
  battery: int("battery").notNull(), // Battery percentage (0-100)
  rssi: int("rssi").notNull(), // Signal strength in dBm
  distance: int("distance"), // Distance measurement if available
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

export type SensorReading = typeof sensorReadings.$inferSelect;
export type InsertSensorReading = typeof sensorReadings.$inferInsert;

/**
 * Route history table - stores calculated routes with all details
 */
export const routeHistory = mysqlTable("routeHistory", {
  id: int("id").autoincrement().primaryKey(),
  routeDate: timestamp("routeDate").defaultNow().notNull(), // Date when route was calculated
  startLocation: varchar("startLocation", { length: 255 }).default("Codeca"), // Starting point (Codeca)
  endLocation: varchar("endLocation", { length: 255 }).default("Codeca"), // Ending point (Codeca)
  totalDistance: float("totalDistance").notNull(), // Total distance in km
  totalDuration: int("totalDuration").notNull(), // Total duration in minutes
  containersCount: int("containersCount").notNull(), // Number of containers in route
  containerIds: text("containerIds").notNull(), // JSON array of container IDs
  polylinePoints: text("polylinePoints").notNull(), // JSON array of route coordinates
  status: mysqlEnum("status", ["planned", "in_progress", "completed", "cancelled"]).default("planned"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type RouteHistory = typeof routeHistory.$inferSelect;
export type InsertRouteHistory = typeof routeHistory.$inferInsert;

/**
 * Route savings table - stores economy metrics for each route
 */
export const routeSavings = mysqlTable("routeSavings", {
  id: int("id").autoincrement().primaryKey(),
  routeId: int("routeId").notNull(), // Foreign key to routeHistory
  fuelSaved: float("fuelSaved").notNull(), // Fuel saved in liters
  co2Saved: float("co2Saved").notNull(), // CO2 saved in kg
  costSaved: float("costSaved").notNull(), // Cost saved in R$
  timeSaved: int("timeSaved").notNull(), // Time saved in minutes
  efficiencyGain: float("efficiencyGain").notNull(), // Efficiency gain percentage
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type RouteSavings = typeof routeSavings.$inferSelect;
export type InsertRouteSavings = typeof routeSavings.$inferInsert;