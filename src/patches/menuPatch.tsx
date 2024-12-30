//Credit: https://github.com/jessebofill/DeckWebBrowser

import { afterPatch, Dropdown, findInReactTree, FooterLegendProps, getReactRoot } from "@decky/ui"
import { FC } from "react"
import { FaDiscord } from "react-icons/fa"

interface MainMenuItemProps extends FooterLegendProps {
    route: string
    label: string
    onFocus: () => void
    onActivate?: () => void
    children?: React.ReactNode
}

const reactTree = getReactRoot(document.getElementById('root') as any);
let unpatchMethod: any;

const _patchMenu = () => {
    const menuNode = findInReactTree(reactTree, (node) => node?.memoizedProps?.navID == 'MainNavMenuContainer')
    if (!menuNode || !menuNode.return?.type) {
        console.log('Menu Patch', 'Failed to find main menu root node.')
        return () => { }
    }
    const orig = menuNode.return.type
    let patchedInnerMenu: any
    const menuWrapper = (props: any) => {
        const ret = orig(props)
        if (!ret?.props?.children?.props?.children?.[0]?.type) {
            console.log('Menu Patch', 'The main menu element could not be found at the expected location. Valve may have changed it.')
            return ret
        }
        if (patchedInnerMenu) {
            ret.props.children.props.children[0].type = patchedInnerMenu
        } else {
            afterPatch(ret.props.children.props.children[0], 'type', (_: any, ret: any) => {
                if (!ret?.props?.children || !Array.isArray(ret?.props?.children)) {
                    console.log('Menu Patch', 'Could not find menu items to patch.');
                    return ret
                }
                const itemIndexes = getMenuItemIndexes(ret.props.children)
                const menuItemElement = findInReactTree(ret.props.children, (x) =>
                    x?.type?.toString()?.includes('exactRouteMatch:'),
                );

                const newItem =
                    <MenuItemWrapper
                        route="/discord"
                        label='Discord'
                        onFocus={menuItemElement.props.onFocus}
                        MenuItemComponent={menuItemElement.type}
                    />

                const browserPosition = Number.parseInt(localStorage.getItem("DECKCORD_MENU_POSITION") || "3" as string);

                if (browserPosition === 9) ret.props.children.splice(itemIndexes[itemIndexes.length - 1] + 1, 0, newItem)
                else ret.props.children.splice(itemIndexes[browserPosition - 1], 0, newItem)

                return ret
            })
            patchedInnerMenu = ret.props.children.props.children[0].type
        }
        return ret;
    }
    menuNode.return.type = menuWrapper
    if (menuNode.return.alternate) {
        menuNode.return.alternate.type = menuNode.return.type;
    }

    return () => {
        menuNode.return.type = orig
        menuNode.return.alternate.type = menuNode.return.type;
    }
}

function getMenuItemIndexes(items: any[]) {
    return items.flatMap((item, index) => (item && item.$$typeof && item.type !== 'div') ? index : [])
}

interface MenuItemWrapperProps extends MainMenuItemProps {
    MenuItemComponent: FC<MainMenuItemProps>
}

const MenuItemWrapper: FC<MenuItemWrapperProps> = ({ MenuItemComponent, ...props }) => {

    const choosePosition: any = new (Dropdown as any)({
        rgOptions: [
            { label: '1', data: 1 },
            { label: '2', data: 2 },
            { label: '3', data: 3 },
            { label: '4', data: 4 },
            { label: '5', data: 5 },
            { label: '6', data: 6 },
            { label: '7', data: 7 },
            { label: '8', data: 8 },
            { label: '9', data: 9 },
        ],
        selectedOption: 1,
        onChange: (data: any) => {
            unpatchMethod();
            localStorage.setItem("DECKCORD_MENU_POSITION", data.data);
            patchMenu();
        }
    });
    return (
        <MenuItemComponent
            {...props}
            onSecondaryActionDescription={ "Change Position" }
            onSecondaryButton={ (_) => choosePosition.ShowMenu() }
        >
            <FaDiscord/>
        </MenuItemComponent>
    )
}

export const patchMenu = () => {
    unpatchMethod = _patchMenu()
    return unpatchMethod;
}