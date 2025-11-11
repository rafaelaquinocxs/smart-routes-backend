CREATE TABLE `containers` (
	`id` int AUTO_INCREMENT NOT NULL,
	`sensorId` varchar(64) NOT NULL,
	`name` varchar(255) NOT NULL,
	`latitude` decimal(10,8) NOT NULL,
	`longitude` decimal(11,8) NOT NULL,
	`capacity` int DEFAULT 100,
	`status` enum('active','inactive','maintenance') DEFAULT 'active',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `containers_id` PRIMARY KEY(`id`),
	CONSTRAINT `containers_sensorId_unique` UNIQUE(`sensorId`)
);
--> statement-breakpoint
CREATE TABLE `sensorReadings` (
	`id` int AUTO_INCREMENT NOT NULL,
	`containerId` int NOT NULL,
	`sensorId` varchar(64) NOT NULL,
	`level` int NOT NULL,
	`battery` int NOT NULL,
	`rssi` int NOT NULL,
	`distance` int,
	`timestamp` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `sensorReadings_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `users` MODIFY COLUMN `openId` varchar(64);--> statement-breakpoint
ALTER TABLE `users` MODIFY COLUMN `loginMethod` varchar(64) DEFAULT 'jwt';--> statement-breakpoint
ALTER TABLE `users` MODIFY COLUMN `role` enum('user','admin','company') NOT NULL DEFAULT 'user';--> statement-breakpoint
ALTER TABLE `users` ADD `passwordHash` varchar(255);--> statement-breakpoint
ALTER TABLE `users` ADD `companyName` text;--> statement-breakpoint
ALTER TABLE `users` ADD CONSTRAINT `users_email_unique` UNIQUE(`email`);