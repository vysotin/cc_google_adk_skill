var __defProp = Object.defineProperty;
var __getOwnPropSymbols = Object.getOwnPropertySymbols;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __propIsEnum = Object.prototype.propertyIsEnumerable;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __spreadValues = (a, b) => {
  for (var prop in b || (b = {}))
    if (__hasOwnProp.call(b, prop))
      __defNormalProp(a, prop, b[prop]);
  if (__getOwnPropSymbols)
    for (var prop of __getOwnPropSymbols(b)) {
      if (__propIsEnum.call(b, prop))
        __defNormalProp(a, prop, b[prop]);
    }
  return a;
};
/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
import { Type } from "@google/genai";
import { z } from "zod";
function isZodObject(obj) {
  var _a;
  return obj !== null && typeof obj === "object" && ((_a = obj._def) == null ? void 0 : _a.typeName) === "ZodObject";
}
function parseZodType(zodType) {
  const def = zodType._def;
  if (!def) {
    return {};
  }
  const description = def.description;
  const result = {};
  if (description) result.description = description;
  const returnResult = (result2) => {
    if (result2.description === void 0) {
      delete result2.description;
    }
    return result2;
  };
  switch (def.typeName) {
    case z.ZodFirstPartyTypeKind.ZodString:
      result.type = Type.STRING;
      for (const check of def.checks || []) {
        if (check.kind === "min")
          result.minLength = check.value.toString();
        else if (check.kind === "max")
          result.maxLength = check.value.toString();
        else if (check.kind === "email")
          result.format = "email";
        else if (check.kind === "uuid")
          result.format = "uuid";
        else if (check.kind === "url")
          result.format = "uri";
        else if (check.kind === "regex")
          result.pattern = check.regex.source;
      }
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodNumber:
      result.type = Type.NUMBER;
      for (const check of def.checks || []) {
        if (check.kind === "min")
          result.minimum = check.value;
        else if (check.kind === "max")
          result.maximum = check.value;
        else if (check.kind === "int")
          result.type = Type.INTEGER;
      }
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodBoolean:
      result.type = Type.BOOLEAN;
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodArray:
      result.type = Type.ARRAY;
      result.items = parseZodType(def.type);
      if (def.minLength) result.minItems = def.minLength.value.toString();
      if (def.maxLength) result.maxItems = def.maxLength.value.toString();
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodObject: {
      const nestedSchema = zodObjectToSchema(zodType);
      return nestedSchema;
    }
    case z.ZodFirstPartyTypeKind.ZodLiteral:
      const literalType = typeof def.value;
      result.enum = [def.value.toString()];
      if (literalType === "string") {
        result.type = Type.STRING;
      } else if (literalType === "number") {
        result.type = Type.NUMBER;
      } else if (literalType === "boolean") {
        result.type = Type.BOOLEAN;
      } else if (def.value === null) {
        result.type = Type.NULL;
      } else {
        throw new Error("Unsupported ZodLiteral value type: ".concat(literalType));
      }
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodEnum:
      result.type = Type.STRING;
      result.enum = def.values;
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodNativeEnum:
      result.type = Type.STRING;
      result.enum = Object.values(def.values);
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodUnion:
      result.anyOf = def.options.map(parseZodType);
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodOptional:
      return parseZodType(def.innerType);
    case z.ZodFirstPartyTypeKind.ZodNullable:
      const nullableInner = parseZodType(def.innerType);
      return nullableInner ? returnResult(__spreadValues({
        anyOf: [nullableInner, { type: Type.NULL }]
      }, description && { description })) : returnResult(__spreadValues({ type: Type.NULL }, description && { description }));
    case z.ZodFirstPartyTypeKind.ZodDefault:
      const defaultInner = parseZodType(def.innerType);
      if (defaultInner) defaultInner.default = def.defaultValue();
      return defaultInner;
    case z.ZodFirstPartyTypeKind.ZodBranded:
      return parseZodType(def.type);
    case z.ZodFirstPartyTypeKind.ZodReadonly:
      return parseZodType(def.innerType);
    case z.ZodFirstPartyTypeKind.ZodNull:
      result.type = Type.NULL;
      return returnResult(result);
    case z.ZodFirstPartyTypeKind.ZodAny:
    case z.ZodFirstPartyTypeKind.ZodUnknown:
      return returnResult(__spreadValues({}, description && { description }));
    default:
      throw new Error("Unsupported Zod type: ".concat(def.typeName));
  }
}
function zodObjectToSchema(schema) {
  if (schema._def.typeName !== z.ZodFirstPartyTypeKind.ZodObject) {
    throw new Error("Expected a ZodObject");
  }
  const shape = schema.shape;
  const properties = {};
  const required = [];
  for (const key in shape) {
    const fieldSchema = shape[key];
    const parsedField = parseZodType(fieldSchema);
    if (parsedField) {
      properties[key] = parsedField;
    }
    let currentSchema = fieldSchema;
    let isOptional = false;
    while (currentSchema._def.typeName === z.ZodFirstPartyTypeKind.ZodOptional || currentSchema._def.typeName === z.ZodFirstPartyTypeKind.ZodDefault) {
      isOptional = true;
      currentSchema = currentSchema._def.innerType;
    }
    if (!isOptional) {
      required.push(key);
    }
  }
  const catchall = schema._def.catchall;
  let additionalProperties = false;
  if (catchall && catchall._def.typeName !== z.ZodFirstPartyTypeKind.ZodNever) {
    additionalProperties = parseZodType(catchall) || true;
  } else {
    additionalProperties = schema._def.unknownKeys === "passthrough";
  }
  return __spreadValues({
    type: Type.OBJECT,
    properties,
    required: required.length > 0 ? required : []
  }, schema._def.description ? { description: schema._def.description } : {});
}
export {
  isZodObject,
  zodObjectToSchema
};
