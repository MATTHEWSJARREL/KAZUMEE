import { PassThrough } from "node:stream";

import type { AppLoadContext, EntryContext } from "react-router";
import { ServerRouter } from "react-router";
import { createReadableStreamFromReadable } from "@react-router/node";
import { renderToPipeableStream } from "react-dom/server";

export const streamTimeout = 5000;

const isIgnorableStreamError = (error: unknown) => {
  const message =
    error instanceof Error ? error.message : String(error ?? "");
  const lowered = message.toLowerCase();
  return (
    lowered.includes("destination stream closed early") ||
    lowered.includes("aborted") ||
    lowered.includes("premature close")
  );
};

export default function handleRequest(
  request: Request,
  responseStatusCode: number,
  responseHeaders: Headers,
  routerContext: EntryContext,
  _loadContext: AppLoadContext,
) {
  return new Promise<Response>((resolve, reject) => {
    let shellRendered = false;
    let settled = false;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    const onAbortRequest = () => {
      abort();
    };

    const finishResolve = (response: Response) => {
      if (settled) return;
      settled = true;
      request.signal.removeEventListener("abort", onAbortRequest);
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      resolve(response);
    };

    const finishReject = (error: unknown) => {
      if (settled) return;
      settled = true;
      request.signal.removeEventListener("abort", onAbortRequest);
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      reject(error);
    };

    const { pipe, abort } = renderToPipeableStream(
      <ServerRouter context={routerContext} url={request.url} />,
      {
        onShellReady() {
          if (request.signal.aborted) {
            return;
          }

          shellRendered = true;
          const body = new PassThrough();
          const stream = createReadableStreamFromReadable(body);
          responseHeaders.set("Content-Type", "text/html");

          body.on("error", (error: unknown) => {
            if (!isIgnorableStreamError(error)) {
              console.error(error);
            }
          });
          body.on("close", () => {
            request.signal.removeEventListener("abort", onAbortRequest);
          });

          finishResolve(
            new Response(stream, {
              headers: responseHeaders,
              status: responseStatusCode,
            }),
          );

          try {
            pipe(body);
          } catch (error) {
            if (!isIgnorableStreamError(error)) {
              finishReject(error);
            }
          }
        },
        onShellError(error: unknown) {
          if (isIgnorableStreamError(error)) {
            return;
          }
          finishReject(error);
        },
        onError(error: unknown) {
          if (isIgnorableStreamError(error)) {
            return;
          }
          responseStatusCode = 500;
          if (shellRendered) {
            console.error(error);
          }
        },
      },
    );

    request.signal.addEventListener("abort", onAbortRequest);

    timeoutId = setTimeout(() => {
      abort();
      request.signal.removeEventListener("abort", onAbortRequest);
    }, streamTimeout + 1000);
  });
}
