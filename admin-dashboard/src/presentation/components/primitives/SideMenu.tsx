"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import styles from "./SideMenu.module.css";

export interface NavItem {
  label: string;
  href: string;
}

export interface SideMenuProps {
  items: NavItem[];
  footer?: React.ReactNode;
}

export function SideMenu({ items, footer }: SideMenuProps) {
  const pathname = usePathname();

  return (
    <nav className={styles.menu}>
      <ul className={styles.list}>
        {items.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={isActive ? `${styles.link} ${styles.active}` : styles.link}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
      {footer ? <div className={styles.footer}>{footer}</div> : null}
    </nav>
  );
}
