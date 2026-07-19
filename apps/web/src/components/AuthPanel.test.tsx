import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuthPanel from "./AuthPanel";

const mocks = vi.hoisted(() => ({
  fetchPrincipal: vi.fn(),
  observeUser: vi.fn(() => () => undefined),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ fetchPrincipal: mocks.fetchPrincipal }));
vi.mock("@/lib/auth", () => ({
  AUTH_MODE: "firebase",
  firebaseConfigured: true,
  observeUser: mocks.observeUser,
  signIn: mocks.signIn,
  signOut: mocks.signOut,
}));

const controller = {
  uid: "firebase-controller-uid",
  displayName: "admin@venuesignal.com",
  role: "CONTROLLER",
  authMode: "firebase",
};

describe("Demo Controller access", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.observeUser.mockReturnValue(() => undefined);
    mocks.signIn.mockResolvedValue({});
    mocks.fetchPrincipal.mockResolvedValue(controller);
  });

  it("communicates the product purpose and safe demo-account instructions", () => {
    render(<AuthPanel onPrincipal={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "AI-assisted incident intelligence for stadium operations." })).toBeVisible();
    expect(screen.getByText("AI proposes. Deterministic logic verifies. Humans decide.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Demo Controller Access" })).toBeVisible();
    expect(screen.getAllByText("admin@venuesignal.com").length).toBeGreaterThan(0);
    expect(screen.getByText("Password provided in submission instructions.")).toBeVisible();
    expect(screen.queryByText(/UID|auth mode|token/i)).not.toBeInTheDocument();
  });

  it("prefills only the demo email and preserves password-manager fields", () => {
    render(<AuthPanel onPrincipal={vi.fn()} />);

    expect(screen.getByLabelText("Email")).toHaveValue("admin@venuesignal.com");
    expect(screen.getByLabelText("Email")).toHaveAttribute("autocomplete", "username");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "current-password");
  });

  it("submits with Enter, verifies the server principal, and shows the controller landing identity", async () => {
    const onPrincipal = vi.fn();
    const user = userEvent.setup();
    render(<AuthPanel onPrincipal={onPrincipal} />);

    await user.type(screen.getByLabelText("Password"), "submission-only-password");
    await user.keyboard("{Enter}");

    await waitFor(() => expect(mocks.signIn).toHaveBeenCalledWith("admin@venuesignal.com", "submission-only-password"));
    await waitFor(() => expect(mocks.fetchPrincipal).toHaveBeenCalledOnce());
    expect(onPrincipal).toHaveBeenCalledWith(controller);
    expect(await screen.findByText("Demo Controller")).toBeVisible();
    expect(screen.getByText("CONTROLLER")).toBeVisible();
    expect(screen.queryByText(controller.uid)).not.toBeInTheDocument();
  });

  it("announces a clear loading state without exposing provider details", async () => {
    let finishSignIn: (() => void) | undefined;
    mocks.signIn.mockImplementation(
      () => new Promise((resolve) => { finishSignIn = () => resolve({}); }),
    );
    const user = userEvent.setup();
    render(<AuthPanel onPrincipal={vi.fn()} />);

    await user.type(screen.getByLabelText("Password"), "submission-only-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();

    finishSignIn?.();
    expect(await screen.findByText("Demo Controller")).toBeVisible();
  });

  it("reports authentication failures concisely and keeps the password private", async () => {
    mocks.signIn.mockRejectedValue(new Error("Firebase: Error (auth/wrong-password)."));
    const user = userEvent.setup();
    render(<AuthPanel onPrincipal={vi.fn()} />);

    await user.type(screen.getByLabelText("Password"), "incorrect-private-value");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to sign in. Check the demo credentials and try again.");
    expect(screen.queryByText(/wrong-password/)).not.toBeInTheDocument();
  });
});
