/**
 * Animation Variants Library
 *
 * Provides reusable animation variant types and class mappings for tailwindcss-motion.
 * These variants can be used with the Animate component for consistent animations.
 */

export type AnimationVariant =
  | 'heroBlur'
  | 'slideUp'
  | 'scaleFade'
  | 'fadeIn'
  | 'zoomIn'
  | 'slideInLeft'
  | 'slideInRight'

/**
 * Map of animation variants to tailwindcss-motion class strings.
 * Each variant combines motion utilities for opacity, transform, blur, duration, and easing.
 */
export const animationVariants: Record<AnimationVariant, string> = {
  // Hero entrance with heavy blur and scale
  heroBlur:
    'motion-blur-in-[6px] motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.5s] motion-duration-[0.7s]/blur motion-ease-spring-smooth',

  // Slide up from below with blur
  slideUp:
    'motion-opacity-in-[0%] motion-translate-y-in-[20px] motion-blur-in-[3px] motion-duration-[0.4s] motion-duration-[0.6s]/blur motion-ease-spring-smooth',

  // Scale and fade in
  scaleFade:
    'motion-scale-in-[0.95] motion-opacity-in-[0%] motion-duration-[0.4s] motion-ease-spring-smooth',

  // Simple fade in
  fadeIn:
    'motion-opacity-in-[0%] motion-duration-[0.3s] motion-ease-spring-smooth',

  // Zoom in with bounce
  zoomIn:
    'motion-scale-in-[0.9] motion-opacity-in-[0%] motion-duration-[0.5s] motion-ease-spring-bouncy',

  // Slide in from left
  slideInLeft:
    'motion-translate-x-in-[-20px] motion-opacity-in-[0%] motion-duration-[0.4s] motion-ease-spring-smooth',

  // Slide in from right
  slideInRight:
    'motion-translate-x-in-[20px] motion-opacity-in-[0%] motion-duration-[0.4s] motion-ease-spring-smooth',
}
