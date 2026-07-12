/**
 * Firebase Authentication Module
 * Handles Firebase Auth integration and token management
 */
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import {
  getAuth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  onAuthStateChanged,
  updateProfile,
} from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js';

import { api, authApi } from './api.js';

// Firebase config - loaded from window.APP_CONFIG (set in HTML)
const firebaseConfig = window.APP_CONFIG?.firebase || {};

let _app = null;
let _auth = null;
let _currentUser = null;

export function initFirebase() {
  if (_app) return _auth;
  _app = initializeApp(firebaseConfig);
  _auth = getAuth(_app);
  return _auth;
}

export function getFirebaseAuth() {
  if (!_auth) initFirebase();
  return _auth;
}

export async function loginWithEmail(email, password) {
  const auth = getFirebaseAuth();
  const cred = await signInWithEmailAndPassword(auth, email, password);
  const idToken = await cred.user.getIdToken();

  // Exchange Firebase token for our JWT
  const tokenData = await authApi.verifyToken(idToken);
  if (tokenData?.access_token) {
    api.setToken(tokenData.access_token);
    _currentUser = cred.user;
    return { user: cred.user, token: tokenData.access_token };
  }
  throw new Error('Failed to get access token');
}

export async function registerWithEmail(email, password, displayName, schoolName) {
  const auth = getFirebaseAuth();
  const cred = await createUserWithEmailAndPassword(auth, email, password);
  await updateProfile(cred.user, { displayName });

  const idToken = await cred.user.getIdToken();
  const tokenData = await authApi.registerWithToken(idToken, displayName, schoolName);
  if (tokenData?.access_token) {
    api.setToken(tokenData.access_token);
    _currentUser = cred.user;
    return { user: cred.user, token: tokenData.access_token };
  }
  throw new Error('Registration failed');
}

export async function logout() {
  const auth = getFirebaseAuth();
  await signOut(auth);
  api.setToken(null);
  _currentUser = null;
  localStorage.removeItem('teacher_data');
  window.location.href = '/pages/login.html';
}

export async function resetPassword(email) {
  const auth = getFirebaseAuth();
  await sendPasswordResetEmail(auth, email);
}

export function onAuthChange(callback) {
  const auth = getFirebaseAuth();
  return onAuthStateChanged(auth, callback);
}

export function getCurrentUser() { return _currentUser; }

export async function requireAuth() {
  const token = api.getToken();
  if (!token) {
    window.location.href = '/pages/login.html';
    return null;
  }
  try {
    const user = await authApi.me();
    return user;
  } catch {
    api.setToken(null);
    window.location.href = '/pages/login.html';
    return null;
  }
}

export function getStoredTeacher() {
  try { return JSON.parse(localStorage.getItem('teacher_data') || 'null'); }
  catch { return null; }
}

export function storeTeacher(data) {
  localStorage.setItem('teacher_data', JSON.stringify(data));
}
