// error-codes.ts
export const ERROR_CODES: Record<number, string> = {
  0: 'Network error: Unable to reach server',
  400: 'Invalid request sent to server',
  401: 'Unauthorized',
  403: 'You do not have permission to perform this action',
  404: 'Requested resource not found',
  409: 'Conflict occurred while processing your request',
  422: 'Validation failed on server',
  429: 'Too many requests. Slow down.',
  500: 'Internal server error',
  502: 'Bad gateway',
  503: 'Service unavailable, try again later',
  504: 'Server taking too long to respond',
};
