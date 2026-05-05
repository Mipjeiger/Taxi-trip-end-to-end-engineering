import { useEffect, useState } from "react";

export const useMobile = () => {
    const [isMobile, setIsMobile] = useState(false);
    const [isPortrait, setIsPortrait] = useState(true);
    const [safeAreaInsets, setSafeAreaInsets] = useState({ top: 0, right: 0, bottom: 0, left: 0 });

    useEffect(() => {
        const checkMobile = () => {
            setIsMobile(window.innerWidth < 768);
            setIsPortrait(window.innerHeight > window.innerWidth);
        };

        const updateSafeArea = () => {
            const root = document.documentElement;
            setSafeAreaInsets({
                top: parseInt(getComputedStyle(root).getPropertyValue("--safe-area-inset-top")) || 0,
                right: parseInt(getComputedStyle(root).getPropertyValue("--safe-area-inset-right")) || 0,
                bottom: parseInt(getComputedStyle(root).getPropertyValue("--safe-area-inset-bottom")) || 0,
                left: parseInt(getComputedStyle(root).getPropertyValue("--safe-area-inset-left")) || 0,
            });
        };
        
        checkMobile();
        updateSafeArea();


        window.addEventListener("resize", checkMobile);
        window.addEventListener('orientationchange', checkMobile);

        return () => {
            window.removeEventListener("resize", checkMobile);
            window.removeEventListener('orientationchange', checkMobile);
        };
    }, []);

    return { isMobile, isPortrait, safeAreaInsets };
};