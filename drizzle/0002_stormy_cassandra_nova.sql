CREATE TABLE `routeHistory` (
	`id` int AUTO_INCREMENT NOT NULL,
	`routeDate` timestamp NOT NULL DEFAULT (now()),
	`startLocation` varchar(255) DEFAULT 'Codeca',
	`endLocation` varchar(255) DEFAULT 'Codeca',
	`totalDistance` float NOT NULL,
	`totalDuration` int NOT NULL,
	`containersCount` int NOT NULL,
	`containerIds` text NOT NULL,
	`polylinePoints` text NOT NULL,
	`status` enum('planned','in_progress','completed','cancelled') DEFAULT 'planned',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `routeHistory_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `routeSavings` (
	`id` int AUTO_INCREMENT NOT NULL,
	`routeId` int NOT NULL,
	`fuelSaved` float NOT NULL,
	`co2Saved` float NOT NULL,
	`costSaved` float NOT NULL,
	`timeSaved` int NOT NULL,
	`efficiencyGain` float NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `routeSavings_id` PRIMARY KEY(`id`)
);
