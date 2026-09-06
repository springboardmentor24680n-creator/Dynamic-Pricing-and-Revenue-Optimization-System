"use client";

import React from "react";
import { ClerkProvider, SignInButton, SignedIn, SignedOut, UserButton, useUser } from "@clerk/nextjs";

interface ClerkAuthWrapperProps {
  children: React.ReactNode;
}

const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "pk_test_bW92aW5nLWxsYW1hLTc3MzEuY2xlcmsuYWNjb3VudHMuZGV2JA";

export const ClerkAuthWrapper: React.FC<ClerkAuthWrapperProps> = ({ children }) => {
  return (
    <ClerkProvider publishableKey={publishableKey}>
      {children}
    </ClerkProvider>
  );
};

export { SignInButton, SignedIn, SignedOut, UserButton, useUser };
