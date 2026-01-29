/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
import { Schema } from '@google/genai';
import { ZodObject } from 'zod';
/**
 * Returns true if the given object is a V3 ZodObject.
 */
export declare function isZodObject(obj: unknown): obj is ZodObject<any>;
export declare function zodObjectToSchema(schema: ZodObject<any>): Schema;
