import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router, protectedProcedure } from "./_core/trpc";
import { z } from "zod";
import { hashPassword, verifyPassword } from "./_core/password";
import { generateToken, setTokenCookie, clearTokenCookie, JWT_COOKIE_NAME } from "./_core/auth";
import { upsertUser, getUserByEmail, getContainers, getLatestSensorReadings, saveRoute, saveRouteSavings, getRouteHistory, getTotalSavings, getSavingsByPeriod, getRouteSavingsByRouteId } from "./db";

function decodePolyline(encoded: string): [number, number][] {
  const points: [number, number][] = [];
  let index = 0, lat = 0, lng = 0;

  while (index < encoded.length) {
    let result = 0, shift = 0;
    let b;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += dlat;

    result = 0;
    shift = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += dlng;

    points.push([lng / 1e5, lat / 1e5]);
  }
  return points;
}

// Codeca (Garage) coordinates - Ponto Zero
const CODECA = {
  lat: -29.1750,
  lng: -51.1850,
  name: 'Codeca (Garagem)',
};

export const appRouter = router({
  system: systemRouter,

  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    
    logout: publicProcedure.mutation(({ ctx }) => {
      clearTokenCookie(ctx.res);
      return {
        success: true,
      } as const;
    }),

    register: publicProcedure
      .input(z.object({
        email: z.string().email(),
        password: z.string().min(6),
        name: z.string().optional(),
        companyName: z.string().optional(),
        role: z.enum(["user", "company"]).default("user"),
      }))
      .mutation(async ({ input, ctx }) => {
        try {
          const existingUser = await getUserByEmail(input.email);
          if (existingUser) {
            throw new Error("Email already registered");
          }

          const passwordHash = await hashPassword(input.password);
          
          await upsertUser({
            email: input.email,
            passwordHash,
            name: input.name,
            companyName: input.companyName,
            role: input.role,
            loginMethod: "jwt",
            lastSignedIn: new Date(),
          });

          const user = await getUserByEmail(input.email);
          if (!user) {
            throw new Error("Failed to create user");
          }

          const token = generateToken({
            userId: user.id,
            email: user.email!,
            role: user.role,
          });

          setTokenCookie(ctx.res, token);

          return {
            success: true,
            user: {
              id: user.id,
              email: user.email,
              name: user.name,
              companyName: user.companyName,
              role: user.role,
            },
          };
        } catch (error) {
          console.error("[Auth] Registration failed:", error);
          throw error;
        }
      }),

    login: publicProcedure
      .input(z.object({
        email: z.string().email(),
        password: z.string(),
      }))
      .mutation(async ({ input, ctx }) => {
        try {
          const user = await getUserByEmail(input.email);
          if (!user || !user.passwordHash) {
            throw new Error("Invalid email or password");
          }

          const isPasswordValid = await verifyPassword(input.password, user.passwordHash);
          if (!isPasswordValid) {
            throw new Error("Invalid email or password");
          }

          const token = generateToken({
            userId: user.id,
            email: user.email!,
            role: user.role,
          });

          setTokenCookie(ctx.res, token);

          return {
            success: true,
            user: {
              id: user.id,
              email: user.email,
              name: user.name,
              companyName: user.companyName,
              role: user.role,
            },
          };
        } catch (error) {
          console.error("[Auth] Login failed:", error);
          throw error;
        }
      }),
  }),

  containers: router({
    list: publicProcedure.query(async () => {
      try {
        const containers = await getContainers();
        return containers;
      } catch (error) {
        console.error("[Containers] List failed:", error);
        return [];
      }
    }),

    readings: publicProcedure.query(async () => {
      try {
        const readings = await getLatestSensorReadings();
        return readings;
      } catch (error) {
        console.error("[Readings] List failed:", error);
        return [];
      }
    }),

    calculateRoute: publicProcedure
      .input(z.object({
        containers: z.array(z.any()),
      }))
      .mutation(async ({ input }) => {
        try {
          const { containers } = input;
          if (!containers || containers.length === 0) {
            throw new Error("No containers provided");
          }

          // Optimize route using nearest neighbor, starting from Codeca
          const waypoints = containers.map((c: any) => ({
            lat: parseFloat(String(c.latitude)),
            lng: parseFloat(String(c.longitude)),
            name: c.name,
          }));

          // Start route from Codeca
          const optimizedRoute = [CODECA];
          const visited = new Set<number>();

          // Build route from Codeca through all containers
          while (visited.size < waypoints.length) {
            const current = optimizedRoute[optimizedRoute.length - 1];
            let nearest = -1;
            let minDistance = Infinity;

            for (let i = 0; i < waypoints.length; i++) {
              if (!visited.has(i)) {
                const dx = waypoints[i].lat - current.lat;
                const dy = waypoints[i].lng - current.lng;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < minDistance) {
                  minDistance = distance;
                  nearest = i;
                }
              }
            }

            if (nearest !== -1) {
              optimizedRoute.push(waypoints[nearest]);
              visited.add(nearest);
            }
          }

          // Return to Codeca at the end
          optimizedRoute.push(CODECA);

          // Get real route from OSRM (Open Source Routing Machine - free, no API key required)
          let allPolylinePoints: [number, number][] = [];
          let totalDistance = 0;
          let totalDuration = 0;

          for (let i = 0; i < optimizedRoute.length - 1; i++) {
            const originLng = optimizedRoute[i].lng;
            const originLat = optimizedRoute[i].lat;
            const destLng = optimizedRoute[i + 1].lng;
            const destLat = optimizedRoute[i + 1].lat;
            
            try {
              const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${originLng},${originLat};${destLng},${destLat}?overview=full&geometries=geojson`;
              console.log(`[Route] Fetching from OSRM: (${originLat},${originLng}) to (${destLat},${destLng})`);
              
              const response = await fetch(osrmUrl);
              const data = await response.json();
              
              console.log(`[Route] OSRM response status:`, response.status);
              console.log(`[Route] OSRM code:`, data.code);

              if (data.code === 'Ok' && data.routes && data.routes[0]) {
                const route = data.routes[0];
                const geometry = route.geometry;
                
                if (geometry && geometry.type === 'LineString' && geometry.coordinates) {
                  allPolylinePoints = allPolylinePoints.concat(geometry.coordinates);
                  
                  // Extract distance and duration
                  const segmentDistance = (route.distance || 0) / 1000; // Convert meters to km
                  const segmentDuration = (route.duration || 0) / 60; // Convert seconds to minutes
                  totalDistance += segmentDistance;
                  totalDuration += segmentDuration;
                  console.log(`[Route] Segment: ${segmentDistance.toFixed(2)} km, ${segmentDuration.toFixed(1)} min`);
                  console.log(`[Route] Added ${geometry.coordinates.length} points from OSRM`);
                }
              } else {
                console.warn(`[Route] OSRM error: ${data.code}`);
                // Fallback: add straight line
                allPolylinePoints.push([originLng, originLat]);
                allPolylinePoints.push([destLng, destLat]);
                
                // Estimate distance using Haversine formula
                const R = 6371; // Earth radius in km
                const dLat = (destLat - originLat) * Math.PI / 180;
                const dLng = (destLng - originLng) * Math.PI / 180;
                const a = Math.sin(dLat/2) * Math.sin(dLat/2) + 
                          Math.cos(originLat * Math.PI / 180) * Math.cos(destLat * Math.PI / 180) *
                          Math.sin(dLng/2) * Math.sin(dLng/2);
                const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
                const distance = R * c;
                totalDistance += distance;
                totalDuration += distance / 40; // Assume 40 km/h average speed
              }
            } catch (error) {
              console.error("[Route] OSRM failed:", error);
              // Fallback: add straight line
              allPolylinePoints.push([originLng, originLat]);
              allPolylinePoints.push([destLng, destLat]);
              
              // Estimate distance using Haversine formula
              const R = 6371; // Earth radius in km
              const dLat = (destLat - originLat) * Math.PI / 180;
              const dLng = (destLng - originLng) * Math.PI / 180;
              const a = Math.sin(dLat/2) * Math.sin(dLat/2) + 
                        Math.cos(originLat * Math.PI / 180) * Math.cos(destLat * Math.PI / 180) *
                        Math.sin(dLng/2) * Math.sin(dLng/2);
              const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
              const distance = R * c;
              totalDistance += distance;
              totalDuration += distance / 40; // Assume 40 km/h average speed
            }
          }

          // Ensure we have valid values
          const finalDistance = totalDistance > 0 ? totalDistance : 0.1;
          const finalDuration = totalDuration > 0 ? totalDuration : 1;

          return {
            polylinePoints: allPolylinePoints.length > 0 ? allPolylinePoints : optimizedRoute.map(p => [p.lng, p.lat]),
            distance: `${finalDistance.toFixed(2)} km`,
            duration: `${Math.round(finalDuration)} min`,
            totalDistance: finalDistance,
            totalDuration: finalDuration,
          };
        } catch (error) {
          console.error("[Route] Calculation failed:", error);
          throw error;
        }
      }),

    saveRoute: publicProcedure
      .input(z.object({
        totalDistance: z.number(),
        totalDuration: z.number(),
        containersCount: z.number(),
        containerIds: z.array(z.number()),
        polylinePoints: z.array(z.array(z.number())),
        fuelSaved: z.number(),
        co2Saved: z.number(),
        costSaved: z.number(),
        timeSaved: z.number(),
        efficiencyGain: z.number(),
      }))
      .mutation(async ({ input }) => {
        try {
          // Save route history
          const routeResult = await saveRoute({
            totalDistance: input.totalDistance,
            totalDuration: Math.round(input.totalDuration),
            containersCount: input.containersCount,
            containerIds: JSON.stringify(input.containerIds),
            polylinePoints: JSON.stringify(input.polylinePoints),
            status: 'completed',
          });

          if (!routeResult) {
            throw new Error("Failed to save route");
          }

          // Get the inserted route ID - Drizzle MySQL returns { insertId: number }
          console.log("[Route] Insert result:", routeResult);
          const routeId = (routeResult as any).insertId || (routeResult as any)[Symbol.for('drizzle.insertId')];
          if (!routeId) {
            console.error("[Route] Failed to extract ID from result:", routeResult);
            throw new Error("Failed to get route ID from insert result");
          }
          console.log("[Route] Saved route with ID:", routeId);

          // Save route savings
          await saveRouteSavings({
            routeId: routeId,
            fuelSaved: input.fuelSaved,
            co2Saved: input.co2Saved,
            costSaved: input.costSaved,
            timeSaved: input.timeSaved,
            efficiencyGain: input.efficiencyGain,
          });

          return {
            success: true,
            routeId: routeId,
          };
        } catch (error) {
          console.error("[Route] Save failed:", error);
          throw error;
        }
      }),

    getHistory: publicProcedure
      .input(z.object({
        limit: z.number().default(100),
      }))
      .query(async ({ input }) => {
        try {
          const routes = await getRouteHistory(input.limit);
          
          // Enrich with savings data
          const enrichedRoutes = await Promise.all(
            routes.map(async (route) => {
              const savings = await getRouteSavingsByRouteId(route.id);
              return {
                ...route,
                savings,
              };
            })
          );

          return enrichedRoutes;
        } catch (error) {
          console.error("[Route] Get history failed:", error);
          return [];
        }
      }),

    getTotalSavings: publicProcedure.query(async () => {
      try {
        return await getTotalSavings();
      } catch (error) {
        console.error("[Route] Get total savings failed:", error);
        return null;
      }
    }),

    getSavingsByPeriod: publicProcedure
      .input(z.object({
        period: z.enum(['day', 'month', 'year']).default('month'),
      }))
      .query(async ({ input }) => {
        try {
          return await getSavingsByPeriod(input.period);
        } catch (error) {
          console.error("[Route] Get savings by period failed:", error);
          return [];
        }
      }),
  }),
});

export type AppRouter = typeof appRouter;
