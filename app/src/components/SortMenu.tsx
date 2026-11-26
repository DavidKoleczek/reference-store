import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import {
  Menu,
  MenuContent,
  MenuGroup,
  MenuGroupLabel,
  MenuRadioGroup,
  MenuRadioItem,
  MenuSeparator,
  MenuTrigger,
} from "@/components/ui/menu";
import type { Choice } from "@/lib/arrange";
import { TEXT } from "@/lib/text";
import { cn } from "@/lib/utils";

/**
 * What a list is sorted by, which way, and what it is grouped by, in one menu as a file manager's Sort menu has
 * them. It stays open while more than one is changed. `fixed` says why the order can't be changed now, such as while
 * the list shows what was searched for.
 */
export function SortMenu<Sort extends string, Grouping extends string>({
  sort,
  descending,
  group,
  sorts,
  groups,
  fixed,
  onSort,
  onDescending,
  onGroup,
}: {
  sort: Sort;
  descending: boolean;
  group?: Grouping;
  sorts: Choice<Sort>[];
  groups?: Choice<Grouping>[];
  fixed?: string;
  onSort: (sort: Sort) => void;
  onDescending: (descending: boolean) => void;
  onGroup?: (group: Grouping) => void;
}) {
  return (
    <Menu>
      <MenuTrigger render={<Button variant="secondary" />}>
        <Icon name="arrow-down" className={cn(!descending && "rotate-180")} />
        {TEXT.sort.button}
        <Icon name="chevron" className="-mr-1 text-ink-muted" />
      </MenuTrigger>
      <MenuContent align="end">
        {fixed ? (
          <p className="max-w-56 px-2 py-1.5 text-ink-muted">{fixed}</p>
        ) : (
          <>
            <MenuRadioGroup
              value={sort}
              onValueChange={(next) => onSort(next as Sort)}
            >
              {sorts.map((each) => (
                <MenuRadioItem key={each.value} value={each.value}>
                  {each.label}
                </MenuRadioItem>
              ))}
            </MenuRadioGroup>
            <MenuSeparator />
            <MenuRadioGroup
              value={descending ? "descending" : "ascending"}
              onValueChange={(next) => onDescending(next === "descending")}
            >
              <MenuRadioItem value="ascending">
                {TEXT.sort.ascending}
              </MenuRadioItem>
              <MenuRadioItem value="descending">
                {TEXT.sort.descending}
              </MenuRadioItem>
            </MenuRadioGroup>
          </>
        )}
        {groups && group !== undefined && onGroup && (
          <>
            <MenuSeparator />
            <MenuGroup>
              <MenuGroupLabel>{TEXT.sort.groupBy}</MenuGroupLabel>
              <MenuRadioGroup
                value={group}
                onValueChange={(next) => onGroup(next as Grouping)}
              >
                {groups.map((each) => (
                  <MenuRadioItem key={each.value} value={each.value}>
                    {each.label}
                  </MenuRadioItem>
                ))}
              </MenuRadioGroup>
            </MenuGroup>
          </>
        )}
      </MenuContent>
    </Menu>
  );
}
