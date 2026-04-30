const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type FieldErrors<T extends string> = Partial<Record<T, string>>;

/** Non-empty after trimming */
export function requireText(value: string, label: string): string | undefined {
  if (!value.trim()) return `${label} is required`;
  return undefined;
}

/** Valid e-mail after trimming */
export function requireEmail(value: string): string | undefined {
  const v = value.trim();
  if (!v) return "Email is required";
  if (!EMAIL_RE.test(v)) return "Enter a valid email address";
  return undefined;
}

/** Integer ≥ min */
export function requireMin(value: number, min: number, label: string): string | undefined {
  if (!Number.isInteger(value) || value < min)
    return `${label} must be ${min} or more`;
  return undefined;
}

/** Returns true when the record contains no defined/non-null entries */
export function hasNoErrors<T extends string>(errors: FieldErrors<T>): boolean {
  return Object.values(errors).every((v) => v == null);
}
