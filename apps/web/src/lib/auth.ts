import { FirebaseApp, getApp, getApps, initializeApp } from "firebase/app";
import {
  Auth,
  browserLocalPersistence,
  getAuth,
  onAuthStateChanged,
  setPersistence,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  User,
} from "firebase/auth";

export const AUTH_MODE = process.env.NEXT_PUBLIC_AUTH_MODE || "disabled";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

export const firebaseConfigured =
  AUTH_MODE === "firebase" && Object.values(firebaseConfig).every(Boolean);

let authInstance: Auth | null = null;

function app(): FirebaseApp {
  if (!firebaseConfigured) throw new Error("Firebase authentication is not configured.");
  return getApps().length ? getApp() : initializeApp(firebaseConfig);
}

export function auth(): Auth | null {
  if (!firebaseConfigured) return null;
  if (!authInstance) {
    authInstance = getAuth(app());
    void setPersistence(authInstance, browserLocalPersistence);
  }
  return authInstance;
}

export async function getAuthToken(): Promise<string | null> {
  const current = auth()?.currentUser;
  return current ? current.getIdToken() : null;
}

export function observeUser(callback: (user: User | null) => void): () => void {
  const instance = auth();
  if (!instance) {
    callback(null);
    return () => undefined;
  }
  return onAuthStateChanged(instance, callback);
}

export async function signIn(email: string, password: string): Promise<User> {
  const instance = auth();
  if (!instance) throw new Error("Firebase authentication is not configured.");
  return (await signInWithEmailAndPassword(instance, email, password)).user;
}

export async function signOut(): Promise<void> {
  const instance = auth();
  if (instance) await firebaseSignOut(instance);
}
