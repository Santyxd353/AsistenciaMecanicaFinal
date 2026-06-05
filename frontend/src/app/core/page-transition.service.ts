import { Injectable } from '@angular/core';
import { Router } from '@angular/router';

type ViewTransitionDocument = Document & {
  startViewTransition?: (callback: () => Promise<boolean>) => { finished: Promise<void> };
};

@Injectable({ providedIn: 'root' })
export class PageTransitionService {
  constructor(private router: Router) {}

  navigate(path: string | unknown[]): void {
    const target = Array.isArray(path) ? path : [path];
    const doc = document as ViewTransitionDocument;

    if (typeof doc.startViewTransition !== 'function') {
      this.router.navigate(target);
      return;
    }

    doc.startViewTransition(() => this.router.navigate(target));
  }
}
