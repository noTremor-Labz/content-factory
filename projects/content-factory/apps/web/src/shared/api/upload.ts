const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1"]);

export function rewriteUploadUrlForBrowser(
  uploadUrl: string,
  browserOrigin: string,
  proxyPrefix = "/__storage_proxy",
): string {
  const targetUrl = new URL(uploadUrl);
  const currentUrl = new URL(browserOrigin);

  if (targetUrl.origin === currentUrl.origin) {
    return targetUrl.toString();
  }

  if (LOCAL_HOSTS.has(targetUrl.hostname) && LOCAL_HOSTS.has(currentUrl.hostname)) {
    return `${currentUrl.origin}${proxyPrefix}${targetUrl.pathname}${targetUrl.search}`;
  }

  return targetUrl.toString();
}

export function resolveUploadUrl(uploadUrl: string, proxyPrefix = "/__storage_proxy"): string {
  if (typeof window === "undefined") {
    return uploadUrl;
  }

  return rewriteUploadUrlForBrowser(uploadUrl, window.location.origin, proxyPrefix);
}
