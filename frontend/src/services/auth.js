// services/auth.js

const API_BASE = "http://127.0.0.1:8000";

/**
 * Login user and store JWT token
 * Uses form-urlencoded (not JSON)
 * Field is 'username' (not 'email')
 * Backend returns: { access_token, token_type }
 */
export async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email);  // ✅ Backend expects 'username' field
  formData.append('password', password);
  
  const response = await fetch(`${API_BASE}/users/login`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body: formData
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Invalid credentials");
  }
  
  const data = await response.json();

  if (data.access_token) {
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("token_type", data.token_type);
  }

  return data;
}

/**
 * Register a new user
 * Body: { name, email, password }
 * Password must meet validation requirements:
 *    - At least 8 characters
 *    - One uppercase letter
 *    - One lowercase letter
 *    - One digit
 *    - One special character
 */
export async function register(name, email, password) {
  const response = await fetch(`${API_BASE}/users`, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json" 
    },
    body: JSON.stringify({ name, email, password })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Registration failed");
  }

  return await response.json();
}

/**
 * Get stored JWT token
 */
export function getToken() {
  return localStorage.getItem("access_token");
}

/**
 * Get token type (usually "bearer")
 */
export function getTokenType() {
  return localStorage.getItem("token_type");
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
  return !!getToken();
}

/**
 * Logout user and clear stored tokens
 */
export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("token_type");
  localStorage.removeItem("user_profile");
}

/**
 * Get user profile from localStorage (cached)
 */
export function getCachedUserProfile() {
  const profile = localStorage.getItem("user_profile");
  return profile ? JSON.parse(profile) : null;
}

/**
 * Cache user profile in localStorage
 */
export function cacheUserProfile(profile) {
  localStorage.setItem("user_profile", JSON.stringify(profile));
}

/**
 * Get current user profile from API
 * GET /users/me with Bearer token
 * Returns: { user_id, name, email }
 */
export async function getCurrentUser() {
  const token = getToken();
  
  if (!token) {
    throw new Error("No authentication token found");
  }

  const response = await fetch(`${API_BASE}/users/me`, {
    headers: {
      "Authorization": `Bearer ${token}`
    }
  });

  if (!response.ok) {
    if (response.status === 401) {
      logout(); // Token expired or invalid
      throw new Error("Session expired. Please login again.");
    }
    throw new Error("Failed to fetch user profile");
  }

  const profile = await response.json();
  cacheUserProfile(profile);
  return profile;
}

/**
 * Validate password strength
 */
export function validatePassword(password) {
  const errors = [];
  
  if (password.length < 8) {
    errors.push("Password must be at least 8 characters long");
  }
  if (!/[A-Z]/.test(password)) {
    errors.push("Password must contain at least one uppercase letter");
  }
  if (!/[a-z]/.test(password)) {
    errors.push("Password must contain at least one lowercase letter");
  }
  if (!/\d/.test(password)) {
    errors.push("Password must contain at least one digit");
  }
  if (!/[!@#$%^&*(),.?":{}|<>_/-]/.test(password)) {
    errors.push("Password must contain at least one special character");
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validate email format
 */
export function validateEmail(email) {
  if (!email) return false;
  return email.includes('@') && email.includes('.');
}

/**
 * Handle API errors and logout if unauthorized
 */
export function handleAuthError(error) {
  if (error.message.includes("401") || error.message.includes("unauthorized")) {
    logout();
    return "Your session has expired. Please login again.";
  }
  return error.message || "An error occurred";
}