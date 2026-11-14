export const PASSWORD_MIN_LENGTH = 6;
export const PASSWORD_MAX_LENGTH = 128;
export const PASSWORD_LENGTH_DESCRIPTION = `${PASSWORD_MIN_LENGTH}–${PASSWORD_MAX_LENGTH} characters`;

export function passwordLengthAllowed(value:string) {
  return value.length >= PASSWORD_MIN_LENGTH && value.length <= PASSWORD_MAX_LENGTH;
}
