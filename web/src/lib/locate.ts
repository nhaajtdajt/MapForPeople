/** Vị trí hiện tại của điện thoại. Trình duyệt chỉ cho định vị trên trang HTTPS (bản trên Render) hoặc localhost. */
export function locateMe(timeoutMs = 10_000): Promise<{ lat: number; lon: number; accuracy: number }> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("Máy này không hỗ trợ định vị"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy }),
      (err) =>
        reject(
          new Error(
            err.code === err.PERMISSION_DENIED
              ? "Bạn chưa cho phép định vị. Hãy bật quyền vị trí cho trang này."
              : "Chưa lấy được vị trí, thử lại sau ít giây",
          ),
        ),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 30_000 },
    );
  });
}
