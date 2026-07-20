/*!
 * Color mode toggler for Bootstrap's docs (https://getbootstrap.com/)
 * Copyright 2011-2022 The Bootstrap Authors
 * Licensed under the Creative Commons Attribution 3.0 Unported License.
 */

(() => {
  'use strict'

  const storedTheme = localStorage.getItem('theme')

  // Global elements
  const base_logo_dark_img = "/media/RailOSLogo_dark.svg"
  const base_logo_light_img = "/media/RailOSLogo.svg"

  // Elements from home Window
  const railos_banner_dark_img = "/media/RailOSBanner_dark.svg"
  const railos_banner_light_img = "/media/RailOSBanner.svg"

  const tools_dark_img = "/media/tools_dark.svg"
  const tools_light_img = "/media/tools.svg"

  const getPreferredTheme = () => {
    if (storedTheme) {
      return storedTheme
    }

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  const setTheme = function (theme) {
    let base_logo = document.getElementById('base_railos_logo')
    let railos_banner_mob = document.getElementById('home_railos_banner_mobile')
    let railos_banner = document.getElementById('home_railos_banner')
    let tools_icon = document.getElementById('home_tools_icon')
    if (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.setAttribute('data-bs-theme', 'dark')
    } else {
      document.documentElement.setAttribute('data-bs-theme', theme)
    }
    if(theme === 'dark') {
      if(base_logo) base_logo.src = base_logo_dark_img
      if(railos_banner_mob) railos_banner_mob.src = railos_banner_dark_img
      if(railos_banner) railos_banner.src = railos_banner_dark_img
      if(tools_icon) tools_icon.src = tools_dark_img
    }
    else {
      if(base_logo) base_logo.src = base_logo_light_img
      if(railos_banner_mob) railos_banner_mob.src = railos_banner_light_img
      if(railos_banner) railos_banner.src = railos_banner_light_img
      if(tools_icon) tools_icon.src = tools_light_img
    }
  }

  setTheme(getPreferredTheme())

  const showActiveTheme = theme => {
    const activeThemeIcon = document.querySelector('.theme-icon-active use')
    const btnToActive = document.querySelector(`[data-bs-theme-value="${theme}"]`)

    document.querySelectorAll('[data-bs-theme-value]').forEach(element => {
      element.classList.remove('active')
    })

    btnToActive.classList.add('active')
  }

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (storedTheme !== 'light' || storedTheme !== 'dark') {
      setTheme(getPreferredTheme())
    }
  })

  window.addEventListener('DOMContentLoaded', () => {
    showActiveTheme(getPreferredTheme())

    document.querySelectorAll('[data-bs-theme-value]')
      .forEach(toggle => {
        toggle.addEventListener('click', () => {
          console.log("PRESSED")
          const theme = toggle.getAttribute('data-bs-theme-value')
          localStorage.setItem('theme', theme)
          setTheme(theme)
          showActiveTheme(theme)
        })
      })
  })
})()